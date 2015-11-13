__FILENAME__ = conftest
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import py

def pytest_runtest_setup(item):
    pytest_mozwebqa = py.test.config.pluginmanager.getplugin("mozwebqa")
    pytest_mozwebqa.TestSetup.api_base_url = item.config.option.api_base_url


def pytest_addoption(parser):
    parser.addoption("--apibaseurl",
                     action="store",
                     dest='api_base_url',
                     metavar='str',
                     default="https://addons-dev.allizom.org",
                     help="specify the api url")


def pytest_funcarg__mozwebqa(request):
    pytest_mozwebqa = py.test.config.pluginmanager.getplugin("mozwebqa")
    return pytest_mozwebqa.TestSetup(request)

########NEW FILE########
__FILENAME__ = addons_api
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import urllib2

import xml.etree.ElementTree as ET


class AddonsAPI:

    def __init__(self, testsetup, search_query):
        """
        This class checks the XML response returned by
        the AddonsAPI on addons.mozilla.org.  The search_query
        parameter is the name of the add-on to search for.
        """
        self.search_query = search_query
        self.api_url = '%s/en-us/firefox/api/1.5/search/%s' % (testsetup.base_url, search_query)
        self.xml_response = ET.parse(urllib2.urlopen(self.api_url))

    def get_addon_name(self):
        """
        returns the value of the name element
        of the first add-on from the xml response.
        """
        name = self._parse_response('name')
        return name.lower()

    def get_addon_type(self):
        """
        returns the value of the type element
        of the first add-on from the xml response.
        """
        addon_type = self._parse_response(relpath='type')
        return addon_type.lower()

    def get_addon_type_id(self):
        """
        returns the id attribute of the type
        element of the the first add-on from
        the xml response.
        """
        addon_type = self._parse_response(relpath='type', attr='id')
        return int(addon_type)

    def get_install_link(self):
        """
        returns the url value of the link element
        of the first add-on from the xml response.
        """
        link = self._parse_response(relpath='install')
        return link.lower()

    def get_daily_users(self):
        """
        returns the value of the daily_users element
        of the first add-on from the xml response
        """
        daily_users = self._parse_response(relpath='daily_users')
        return int(daily_users)

    def get_addon_status_id(self):
        """
        returns the id attribute of the status element
        of the first add-on from the xml response.
        """
        status_id = self._parse_response(relpath='status', attr='id')
        return int(status_id)

    def get_addon_status(self):
        """
        returns the status element
        of the first add-on from the xml response.
        """
        status = self._parse_response(relpath='status')
        return status.lower()

    def get_reviews_count(self):
        """
        returns the num attribute of reviews element
        of the first add-on from the xml response.
        """
        count = self._parse_response(relpath='reviews', attr='num')
        return int(count)

    def get_home_page(self):
        """
        returns text of the homepage element
        of the first add-on from the xml response.
        """
        homepage = self._parse_response(relpath='homepage')
        return homepage.lower()

    def get_devs_comments(self):
        """
        returns text of the developer_comments element
        of the first add-on from the xml response.
        all HTML tags are stripped.
        """
        devs_comments = self._parse_response(relpath='developer_comments')
        return self._remove_html_tags(devs_comments)

    def get_learn_more_url(self):
        """
        returns text of the learnmore element
        of the first add-on from the xml response.
        """
        return self._parse_response(relpath='learnmore')

    def get_total_downloads(self):
        """
        returns the total_downloads element
        of the first add-on from the xml response.
        """
        downloads = self._parse_response(relpath='total_downloads')
        return int(downloads)

    def get_compatible_applications(self):
        """
        returns name, min version and max version of
        compatible application of the first add-on from the xml response.
        """
        xpath = 'compatible_applications/application/'
        name_path = xpath + 'name'
        min_ver_path = xpath + 'min_version'
        max_ver_path = xpath + 'max_version'

        return map(self._parse_response,
                   [name_path, min_ver_path, max_ver_path])

    def get_rating(self):
        """
        returns text of the rating element
        of the first add-on from the xml response.
        """
        return self._parse_response(relpath='rating')

    def get_support_url(self):
        """
        returns text of the support element
        of the first add-on from the xml response.
        """
        return self._parse_response(relpath='support')

    def get_icon_url(self):
        """
        returns text of the first icon element
        of the first add-on from the xml response.
        """
        return self._parse_response(relpath='icon')

    def get_addon_description(self):
        """
        returns text of the description element
        of the first add-on from the xml response.
        all HTML tags are stripped.
        """
        desc = self._parse_response(relpath='description')
        return self._remove_html_tags(desc)

    def get_addon_summary(self):
        """
        returns text of the summary element
        of the first add-on from the xml response.
        """
        return self._parse_response(relpath='summary')

    def get_list_of_addon_author_names(self):
        """
        returns list of author names of the first add-on
        from the xml response
        """
        authors_el = self._get_element(relpath='authors')
        authors_list = []
        for child in authors_el:
            authors_list.append(child.find('name').text)
        return authors_list

    def get_list_of_addon_images_links(self):
        """
        returns list of thumbnail image links
        of the first add-on from xml response
        """
        preview_el = self._get_element(relpath='previews')
        link_list = []
        for child in preview_el:
            link = child.find('thumbnail').text
            link_list.append(link.strip())
        return link_list

    def _parse_response(self, relpath, attr=None):
        """
        returns text node of element or attribute of element
        of the first add-on from xml response.
        """
        try:
            el = self.xml_response.getroot().find('./addon/%s' % relpath)
            return attr and el.attrib[attr] or el.text
        except (AttributeError, KeyError):
            raise ET.ParseError(self._error_message(relpath, attr))

    def _get_element(self, relpath):
        """returns element of the first add-on from xml response."""
        try:
            return self.xml_response.getroot().find('./addon/%s' % relpath)
        except AttributeError:
            raise ET.ParseError(self._error_message(relpath))

    def _remove_html_tags(self, text):
        """removes all HTML tags from given string"""
        return re.sub(r'<.*?>', '', text)

    def _error_message(self, relpath, attr=None):
        """generates error message text"""
        if attr:
            err_msg = 'Could not find the attribute [%s] of element [%s]' % (attr, relpath)
        else:
            err_msg = 'Could not find the element [%s]' % relpath

        return err_msg + ' for [%s] add-on. %s' % (self.search_query, self.api_url)

########NEW FILE########
__FILENAME__ = addons_site
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait

from pages.desktop.base import Base


class WriteReviewBlock(Base):

    _add_review_input_field_locator = (By.ID, "id_body")
    _add_review_input_rating_locator = (By.CSS_SELECTOR, '.ratingwidget.stars.stars-0 > label')
    _add_review_submit_button_locator = (By.CSS_SELECTOR, "#review-box input[type=submit]")

    _add_review_box = (By.CSS_SELECTOR, '#review-box')

    def enter_review_with_text(self, text):
        self.selenium.find_element(*self._add_review_input_field_locator).send_keys(text)

    def set_review_rating(self, rating):
        locator = self.selenium.find_element(self._add_review_input_rating_locator[0],
                                             '%s[data-stars="%s"]' % (self._add_review_input_rating_locator[1], rating))
        ActionChains(self.selenium).move_to_element(locator).\
            click().perform()

    def click_to_save_review(self):
        self.selenium.find_element(*self._add_review_submit_button_locator).click()
        return ViewReviews(self.testsetup)

    @property
    def is_review_box_visible(self):
        return self.is_element_visible(*self._add_review_box)


class ViewReviews(Base):

    _review_locator = (By.CSS_SELECTOR, 'div.review:not(.reply)')

    @property
    def reviews(self):
        """Returns review object with index."""
        return [self.ReviewSnippet(self.testsetup, web_element) for web_element in self.selenium.find_elements(*self._review_locator)]

    @property
    def paginator(self):
        from pages.desktop.regions.paginator import Paginator
        return Paginator(self.testsetup)

    class ReviewSnippet(Base):

        _review_text_locator = (By.CSS_SELECTOR, ".description")
        _review_rating_locator = (By.CSS_SELECTOR, "span.stars")
        _review_author_locator = (By.CSS_SELECTOR, "a:not(.permalink)")
        _review_date_locator = (By.CSS_SELECTOR, ".byline")
        _delete_review_locator = (By.CSS_SELECTOR, '.delete-review')
        _delete_review_mark_locator = (By.CSS_SELECTOR, '.item-actions > li:nth-child(2)')

        def __init__(self, testsetup, element):
            Base.__init__(self, testsetup)
            self._root_element = element

        @property
        def text(self):
            return self._root_element.find_element(*self._review_text_locator).text

        @property
        def rating(self):
            return int(self._root_element.find_element(*self._review_rating_locator).text.split()[1])

        @property
        def author(self):
            return self._root_element.find_element(*self._review_author_locator).text

        @property
        def date(self):
            date = self._root_element.find_element(*self._review_date_locator).text
            # we need to parse the string first to get date
            date = re.match('^(.+on\s)([A-Za-z]+\s[\d]+,\s[\d]+)', date)
            return date.group(2)

        def delete(self):
            self._root_element.find_element(*self._delete_review_locator).click()
            WebDriverWait(self.selenium, self.timeout).until(lambda s:
                                                         self.marked_for_deletion == 'Marked for deletion')

        @property
        def marked_for_deletion(self):
            return self._root_element.find_element(*self._delete_review_mark_locator).text


class UserFAQ(Base):

    _license_question_locator = (By.CSS_SELECTOR, '#license')
    _license_answer_locator = (By.CSS_SELECTOR, '#license + dd')
    _page_header_locator = (By.CSS_SELECTOR, '.prose > header > h2')

    @property
    def header_text(self):
        return self.selenium.find_element(*self._page_header_locator).text

    @property
    def license_question(self):
        return self.selenium.find_element(*self._license_question_locator).text

    @property
    def license_answer(self):
        return self.selenium.find_element(*self._license_answer_locator).text


class ViewAddonSource(Base):

    _file_viewer_locator = (By.ID, 'file-viewer')

    @property
    def is_file_viewer_visible(self):
        return self.is_element_visible(*self._file_viewer_locator)

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re

from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait

from pages.page import Page


class Base(Page):

    _amo_logo_locator = (By.CSS_SELECTOR, ".site-title")
    _amo_logo_link_locator = (By.CSS_SELECTOR, ".site-title a")
    _amo_logo_image_locator = (By.CSS_SELECTOR, ".site-title img")

    _footer_locator = (By.CSS_SELECTOR, "#footer")

    def login(self, method="normal", user="default"):
        from pages.desktop.user import Login

        if method == "normal":
            login = self.header.click_login_normal()
            login.login_user_normal(user)

        elif method == "browserID":
            is_browserid_login_available = self.header.is_browserid_login_available

            if is_browserid_login_available:
                login = self.header.click_login_browser_id()
                login.login_user_browser_id(user)
            else:
                login = self.header.click_login_normal()
                login.login_user_normal(user)

    @property
    def page_title(self):
        WebDriverWait(self.selenium, self.timeout).until(lambda s: self.selenium.title)
        return self.selenium.title

    @property
    def is_amo_logo_visible(self):
        return self.is_element_visible(*self._amo_logo_locator)

    def click_amo_logo(self):
        self.selenium.find_element(*self._amo_logo_locator).click()
        from pages.desktop.home import Home
        return Home(self.testsetup)

    @property
    def amo_logo_title(self):
        return self.selenium.find_element(*self._amo_logo_link_locator).get_attribute('title')

    @property
    def amo_logo_text(self):
        return self.selenium.find_element(*self._amo_logo_link_locator).text

    @property
    def amo_logo_image_source(self):
        return self.selenium.find_element(*self._amo_logo_image_locator).get_attribute('src')

    def credentials_of_user(self, user):
        return self.parse_yaml_file(self.credentials)[user]

    @property
    def header(self):
        return Base.HeaderRegion(self.testsetup)

    def search_for(self, search_term):
        self.header.search_for(search_term)
        from pages.desktop.collections import Collections, CollectionSearchResultList
        from pages.desktop.themes import Themes, ThemesSearchResultList
        from pages.desktop.complete_themes import CompleteThemes, CompleteThemesSearchResultList
        if isinstance(self, (Collections, CollectionSearchResultList)):
            return CollectionSearchResultList(self.testsetup)
        elif isinstance(self, (Themes, ThemesSearchResultList)):
            return ThemesSearchResultList(self.testsetup)
        elif isinstance(self, (CompleteThemes, CompleteThemesSearchResultList)):
            return CompleteThemesSearchResultList(self.testsetup)
        else:
            from pages.desktop.search import SearchResultList
            return SearchResultList(self.testsetup)

    @property
    def breadcrumbs(self):
        from pages.desktop.regions.breadcrumbs import Breadcrumbs
        return Breadcrumbs(self.testsetup).breadcrumbs

    def _extract_iso_dates(self, date_format, *locator):
        """
        Returns a list of iso formatted date strings extracted from
        the text elements matched by the given xpath_locator and
        original date_format.

        So for example, given the following elements:
          <p>Added May 09, 2010</p>
          <p>Added June 11, 2011</p>

        A call to:
          _extract_iso_dates("//p", "Added %B %d, %Y", 2)

        Returns:
          ['2010-05-09T00:00:00','2011-06-11T00:00:00']
        """
        addon_dates = [element.text for element in self.selenium.find_elements(*locator)]

        iso_dates = [
            datetime.strptime(s, date_format).isoformat()
            for s in addon_dates
        ]
        return iso_dates

    def _extract_integers(self, regex_pattern, *locator):
        """
        Returns a list of integers extracted from the text elements
        matched by the given xpath_locator and regex_pattern.
        """
        addon_numbers = [element.text for element in self.selenium.find_elements(*locator)]

        integer_numbers = [
            int(re.search(regex_pattern, str(x).replace(",", "")).group(1))
            for x in addon_numbers
        ]
        return integer_numbers

    class HeaderRegion(Page):

        #other applications
        _other_applications_locator = (By.ID, "other-apps")
        _other_applications_menu_locator = (By.CLASS_NAME, "other-apps")

        #Search box
        _search_button_locator = (By.CSS_SELECTOR, ".search-button")
        _search_textbox_locator = (By.ID, "search-q")

        #Not LoggedIn
        _login_browser_id_locator = (By.CSS_SELECTOR, "a.browserid-login")
        _register_locator = (By.CSS_SELECTOR, "#aux-nav li.account a:nth-child(1)")
        _login_normal_locator = (By.CSS_SELECTOR, "#aux-nav li.account a:nth-child(2)")

        #LoggedIn
        _account_controller_locator = (By.CSS_SELECTOR, "#aux-nav .account a.user")
        _account_dropdown_locator = (By.CSS_SELECTOR, "#aux-nav .account ul")
        _logout_locator = (By.CSS_SELECTOR, "li.nomenu.logout > a")

        _site_navigation_menus_locator = (By.CSS_SELECTOR, "#site-nav > ul > li")
        _site_navigation_min_number_menus = 4
        _complete_themes_menu_locator = (By.CSS_SELECTOR, '#site-nav div > a.complete-themes > b')

        def site_navigation_menu(self, value):
            #used to access one specific menu
            for menu in self.site_navigation_menus:
                if menu.name == value.upper():
                    return menu
            raise Exception("Menu not found: '%s'. Menus: %s" % (value, [menu.name for menu in self.site_navigation_menus]))

        @property
        def site_navigation_menus(self):
            #returns a list containing all the site navigation menus
            WebDriverWait(self.selenium, self.timeout).until(lambda s: len(s.find_elements(*self._site_navigation_menus_locator)) >= self._site_navigation_min_number_menus)
            from pages.desktop.regions.header_menu import HeaderMenu
            return [HeaderMenu(self.testsetup, web_element) for web_element in self.selenium.find_elements(*self._site_navigation_menus_locator)]

        def click_complete_themes(self):
            self.selenium.maximize_window()
            themes_menu = self.selenium.find_element(By.CSS_SELECTOR, '#themes')
            complete_themes_menu = self.selenium.find_element(*self._complete_themes_menu_locator)
            ActionChains(self.selenium).move_to_element(themes_menu).\
                move_to_element(complete_themes_menu).click().\
                perform()
            from pages.desktop.complete_themes import CompleteThemes
            return CompleteThemes(self.testsetup)

        def click_other_application(self, other_app):
            hover_locator = self.selenium.find_element(*self._other_applications_locator)
            app_locator = self.selenium.find_element(By.CSS_SELECTOR,
                                                     "#app-%s > a" % other_app.lower())
            ActionChains(self.selenium).move_to_element(hover_locator).\
                move_to_element(app_locator).\
                click().perform()

        def is_other_application_visible(self, other_app):
            hover_locator = self.selenium.find_element(*self._other_applications_locator)
            app_locator = (By.CSS_SELECTOR, "#app-%s" % other_app.lower())
            ActionChains(self.selenium).move_to_element(hover_locator).perform()
            return self.is_element_visible(*app_locator)

        def search_for(self, search_term):
            search_box = self.selenium.find_element(*self._search_textbox_locator)
            search_box.send_keys(search_term)
            self.selenium.find_element(*self._search_button_locator).click()

        @property
        def search_field_placeholder(self):
            return self.selenium.find_element(*self._search_textbox_locator).get_attribute('placeholder')

        @property
        def is_search_button_visible(self):
            return self.is_element_visible(*self._search_button_locator)

        @property
        def is_search_textbox_visible(self):
            return self.is_element_visible(*self._search_textbox_locator)

        @property
        def search_button_title(self):
            return self.selenium.find_element(*self._search_button_locator).get_attribute('title')

        def click_login_browser_id(self):
            self.selenium.find_element(*self._login_browser_id_locator).click()
            from pages.desktop.user import Login
            return Login(self.testsetup)

        def click_login_normal(self):
            self.selenium.find_element(*self._login_normal_locator).click()
            from pages.desktop.user import Login
            return Login(self.testsetup)

        @property
        def is_browserid_login_available(self):
            return self.is_element_present(*self._login_browser_id_locator)

        @property
        def is_login_link_visible(self):
            return self.is_element_visible(*self._login_normal_locator)

        @property
        def is_register_link_visible(self):
            return self.is_element_visible(*self._register_locator)

        def click_logout(self):
            hover_element = self.selenium.find_element(*self._account_controller_locator)
            click_element = self.selenium.find_element(*self._logout_locator)
            ActionChains(self.selenium).move_to_element(hover_element).\
                move_to_element(click_element).\
                click().perform()

        def click_edit_profile(self):
            item_locator = (By.CSS_SELECTOR, " li:nth-child(2) a")
            hover_element = self.selenium.find_element(*self._account_controller_locator)
            click_element = self.selenium.find_element(*self._account_dropdown_locator).find_element(*item_locator)
            ActionChains(self.selenium).move_to_element(hover_element).\
                move_to_element(click_element).\
                click().perform()

            from pages.desktop.user import EditProfile
            return EditProfile(self.testsetup)

        def click_view_profile(self):
            item_locator = (By.CSS_SELECTOR, " li:nth-child(1) a")
            hover_element = self.selenium.find_element(*self._account_controller_locator)
            click_element = self.selenium.find_element(*self._account_dropdown_locator).find_element(*item_locator)
            ActionChains(self.selenium).move_to_element(hover_element).\
                move_to_element(click_element).\
                click().perform()

            from pages.desktop.user import ViewProfile
            view_profile_page = ViewProfile(self.testsetup)
            # Force a wait for the view_profile_page
            view_profile_page.is_the_current_page
            return ViewProfile(self.testsetup)

        def click_my_collections(self):
            item_locator = (By.CSS_SELECTOR, " li:nth-child(3) a")
            hover_element = self.selenium.find_element(*self._account_controller_locator)
            click_element = self.selenium.find_element(*self._account_dropdown_locator).find_element(*item_locator)
            ActionChains(self.selenium).move_to_element(hover_element).\
                move_to_element(click_element).\
                click().perform()

            from pages.desktop.user import MyCollections
            return MyCollections(self.testsetup)

        def click_my_favorites(self):
            item_locator = (By.CSS_SELECTOR, " li:nth-child(4) a")
            hover_element = self.selenium.find_element(*self._account_controller_locator)
            click_element = self.selenium.find_element(*self._account_dropdown_locator).find_element(*item_locator)

            # this method is flakey, it sometimes does not actually click
            ActionChains(self.selenium).move_to_element(hover_element).\
                move_to_element(click_element).\
                click().perform()

            from pages.desktop.user import MyFavorites
            return MyFavorites(self.testsetup)

        @property
        def is_my_favorites_menu_present(self):
            hover_element = self.selenium.find_element(*self._account_controller_locator)

            ActionChains(self.selenium).move_to_element(hover_element).perform()
            menu_text = self.selenium.find_element(*self._account_dropdown_locator).text

            if not 'My Profile' in menu_text:
                print "ActionChains is being flakey again"
            return 'My Favorites' in menu_text

        @property
        def is_user_logged_in(self):
            return self.is_element_visible(*self._account_controller_locator)

        @property
        def menu_name(self):
            return self.selenium.find_element(*self._other_applications_locator).text

        def hover_over_other_apps_menu(self):
            hover_element = self.selenium.find_element(*self._other_applications_locator)
            ActionChains(self.selenium).\
                move_to_element(hover_element).\
                perform()

        @property
        def is_other_apps_dropdown_menu_visible(self):
            return self.selenium.find_element(*self._other_applications_menu_locator).is_displayed()

########NEW FILE########
__FILENAME__ = category
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By

from pages.desktop.base import Base


class Category(Base):

    _categories_side_navigation_header_locator = (By.CSS_SELECTOR, "#side-nav > h2:nth-of-type(2)")
    _categories_alert_update_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(1) > a")
    _categories_appearance_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(2) > a")
    _categories_bookmarks_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(3) > a")
    _categories_download_management_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(4) > a")
    _categories_feed_news_blog_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(5) > a")
    _categories_games_entertainment_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(6) > a")
    _categories_language_support_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(7) > a")
    _categories_photo_music_video_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(8) > a")
    _categories_privacy_security_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(9) > a")
    _categories_search_tools_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(10) > a")
    _categories_shopping_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(11) > a")
    _categories_social_communication_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(12) > a")
    _categories_tabs_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(13) > a")
    _categories_web_development_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(14) > a")
    _categories_other_link_locator = (By.CSS_SELECTOR, "#side-categories > li:nth-of-type(15) > a")

    @property
    def categories_side_navigation_header_text(self):
        return self.selenium.find_element(*self._categories_side_navigation_header_locator).text

    @property
    def categories_alert_updates_header_text(self):
        return self.selenium.find_element(*self._categories_alert_update_link_locator).text

    @property
    def categories_appearance_header_text(self):
        return self.selenium.find_element(*self._categories_appearance_link_locator).text

    @property
    def categories_bookmark_header_text(self):
        return self.selenium.find_element(*self._categories_bookmarks_link_locator).text

    @property
    def categories_download_management_header_text(self):
        return self.selenium.find_element(*self._categories_download_management_link_locator).text

    @property
    def categories_feed_news_blog_header_text(self):
        return self.selenium.find_element(*self._categories_feed_news_blog_link_locator).text

    @property
    def categories_games_entertainment_header_text(self):
        return self.selenium.find_element(*self._categories_games_entertainment_link_locator).text

    @property
    def categories_language_support_header_text(self):
        return self.selenium.find_element(*self._categories_language_support_link_locator).text

    @property
    def categories_photo_music_video_header_text(self):
        return self.selenium.find_element(*self._categories_photo_music_video_link_locator).text

    @property
    def categories_privacy_security_header_text(self):
        return self.selenium.find_element(*self._categories_privacy_security_link_locator).text

    @property
    def categories_shopping_header_text(self):
        return self.selenium.find_element(*self._categories_shopping_link_locator).text

    @property
    def categories_social_communication_header_text(self):
        return self.selenium.find_element(*self._categories_social_communication_link_locator).text

    @property
    def categories_tabs_header_text(self):
        return self.selenium.find_element(*self._categories_tabs_link_locator).text

    @property
    def categories_web_development_header_text(self):
        return self.selenium.find_element(*self._categories_web_development_link_locator).text

    @property
    def categories_other_header_text(self):
        return self.selenium.find_element(*self._categories_other_link_locator).text

########NEW FILE########
__FILENAME__ = collections
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By

from pages.desktop.base import Base
from pages.page import Page
from pages.desktop.search import SearchResultList


class Collections(Base):

    _page_title = "Featured Collections :: Add-ons for Firefox"
    _default_selected_tab_locator = (By.CSS_SELECTOR, "#sorter li.selected")
    _collection_name = (By.CSS_SELECTOR, "h2.collection > span")
    _create_a_collection_locator = (By.CSS_SELECTOR, "#side-nav .button")

    @property
    def collection_name(self):
        return self.selenium.find_element(*self._collection_name).text

    @property
    def default_selected_tab(self):
        return self.selenium.find_element(*self._default_selected_tab_locator).text

    def click_create_collection_button(self):
        self.selenium.find_element(*self._create_a_collection_locator).click()
        return self.CreateNewCollection(self.testsetup)

    class UserCollections(Page):

        _collections_locator = (By.CSS_SELECTOR, ".featured-inner div.item")
        _no_results_locator = (By.CSS_SELECTOR, ".featured-inner > p.no-results")

        @property
        def collections(self):
            return self.selenium.find_elements(*self._collections_locator)

        @property
        def has_no_results(self):
            return self.is_element_present(*self._no_results_locator)

    class CreateNewCollection(Page):

        _name_field_locator = (By.ID, "id_name")
        _description_field_locator = (By.ID, "id_description")
        _create_collection_button_locator = (By.CSS_SELECTOR, ".featured-inner>form>p>input")

        def type_name(self, value):
            self.selenium.find_element(*self._name_field_locator).send_keys(value)

        def type_description(self, value):
            self.selenium.find_element(*self._description_field_locator).send_keys('Description is ' + value)

        def click_create_collection(self):
            self.selenium.find_element(*self._create_collection_button_locator).click()
            return Collection(self.testsetup)


class Collection(Base):

    _notification_locator = (By.CSS_SELECTOR, ".notification-box.success h2")
    _collection_name_locator = (By.CSS_SELECTOR, ".collection > span")
    _delete_collection_locator = (By.CSS_SELECTOR, ".delete")
    _delete_confirmation_locator = (By.CSS_SELECTOR, ".section > form > button")
    _breadcrumb_locator = (By.ID, "breadcrumbs")

    @property
    def notification(self):
        return self.selenium.find_element(*self._notification_locator).text

    @property
    def collection_name(self):
        return self.selenium.find_element(*self._collection_name_locator).text

    def delete(self):
        self.selenium.find_element(*self._delete_collection_locator).click()

    def delete_confirmation(self):
        self.selenium.find_element(*self._delete_confirmation_locator).click()
        return Collections.UserCollections(self.testsetup)

    @property
    def breadcrumb(self):
        return self.selenium.find_element(*self._breadcrumb_locator).text


class CollectionSearchResultList(SearchResultList):
    _results_locator = (By.CSS_SELECTOR, "div.featured-inner div.item")

    class CollectionsSearchResultItem(SearchResultList.SearchResultItem):
        _name_locator = (By.CSS_SELECTOR, 'h3 > a')

########NEW FILE########
__FILENAME__ = complete_themes
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from pages.desktop.regions.sorter import Sorter
from pages.desktop.base import Base
from pages.page import Page
from pages.desktop.search import SearchResultList


class CompleteThemes(Base):

    _addons_root_locator = (By.CSS_SELECTOR, '.listing-grid > li')
    _addon_name_locator = (By.CSS_SELECTOR, 'h3')
    _addons_metadata_locator = (By.CSS_SELECTOR, '.vital .updated')
    _addons_download_locator = (By.CSS_SELECTOR, '.downloads.adu')
    _addons_rating_locator = (By.CSS_SELECTOR, 'span span')
    _category_locator = (By.CSS_SELECTOR, '#c-30 > a')
    _categories_locator = (By.CSS_SELECTOR, '#side-categories li')
    _category_link_locator = (By.CSS_SELECTOR, _categories_locator[1] + ':nth-of-type(%s) a')
    _next_link_locator = (By.CSS_SELECTOR, '.paginator .rel > a:nth-child(3)')
    _previous_link_locator = (By.CSS_SELECTOR, '.paginator .rel > a:nth-child(2)')
    _last_page_link_locator = (By.CSS_SELECTOR, '.rel > a:nth-child(4)')
    _explore_filter_links_locators = (By.CSS_SELECTOR, '#side-explore a')

    @property
    def _addons_root_element(self):
        return self.selenium.find_element(*self._addons_root_locator)

    def click_sort_by(self, type):
        Sorter(self.testsetup).sort_by(type)

    @property
    def sorted_by(self):
        return Sorter(self.testsetup).sorted_by

    @property
    def selected_explore_filter(self):
        for link in self.selenium.find_elements(*self._explore_filter_links_locators):
            selected = link.value_of_css_property('font-weight')
            if selected == 'bold' or int(selected) > 400:
                return link.text

    def click_on_first_addon(self):
        self._addons_root_element.find_element(*self._addon_name_locator).click()
        return CompleteTheme(self.testsetup)

    def click_on_first_category(self):
        self.selenium.find_element(*self._category_locator).click()
        return CompleteThemesCategory(self.testsetup)

    def get_category(self, lookup):
        return self.selenium.find_element(self._category_link_locator[0],
                                          self._category_link_locator[1] % lookup).text

    @property
    def complete_themes_category(self):
        return self.selenium.find_element(*self._category_locator).text

    @property
    def categories_count(self):
        return len(self.selenium.find_elements(*self._categories_locator))

    @property
    def get_all_categories(self):
        return [element.text for element in self.selenium.find_elements(*self._categories_locator)]

    @property
    def addon_names(self):
        addon_name = []
        for addon in self._addons_root_element.find_elements(*self._addon_name_locator):
            ActionChains(self.selenium).move_to_element(addon).perform()
            addon_name.append(addon.text)
        return addon_name

    def addon_name(self, lookup):
        return self.selenium.find_element(By.CSS_SELECTOR,
                                          "%s:nth-of-type(%s) h3" % (self._addons_root_locator[1], lookup)).text

    @property
    def addon_count(self):
        return len(self._addons_root_element.find_elements(*self._addon_name_locator))

    @property
    def addon_updated_dates(self):
        return self._extract_iso_dates("Updated %B %d, %Y", *self._addons_metadata_locator)

    @property
    def addon_created_dates(self):
        return self._extract_iso_dates("Added %B %d, %Y", *self._addons_metadata_locator)

    @property
    def addon_download_number(self):
        pattern = "(\d+(?:[,]\d+)*) weekly downloads"
        downloads = self._extract_integers(pattern, *self._addons_download_locator)
        return downloads

    @property
    def addon_rating(self):
        pattern = "(\d)"
        ratings = self._extract_integers(pattern, *self._addons_rating_locator)
        return ratings

    @property
    def complete_themes(self):
        return [self.CompleteTheme(self.testsetup, completetheme)for completetheme in self.selenium.find_elements(*self._addons_root_locator)]

    @property
    def paginator(self):
        from pages.desktop.regions.paginator import Paginator
        return Paginator(self.testsetup)

    class CompleteTheme(Page):

        _is_incompatible_locator = (By.CSS_SELECTOR, "div.hovercard > span.notavail")
        _not_available_locator = (By.CSS_SELECTOR, "div.hovercard.incompatible > div.more > div.install-shell > div.extra > span.notavail")
        _hovercard_locator = (By.CSS_SELECTOR, "div.hovercard")
        _more_flyout_locator = (By.CSS_SELECTOR, 'div.more')

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        def _move_to_complete_theme_flyout(self):
            # Due to the grid like movement of the mouse and overlapping of hover cards
            # sometimes the wrong hovercard can stick open. First we move the mouse to
            # a location below the hover then move up to ensure we hover on the correct one
            ActionChains(self.selenium).\
                move_to_element_with_offset(self._root_element, 200, 10).\
                move_to_element(self._root_element).\
                perform()

        @property
        def is_flyout_visible(self):
            return self._root_element.find_element(*self._more_flyout_locator).is_displayed()

        @property
        def is_incompatible(self):
            return 'incompatible' in self._root_element.find_element(*self._hovercard_locator).get_attribute('class')

        @property
        def not_available_flag_text(self):
            # This refers to the red 'not available for Firefox x' text inside the flyout
            # We need to move the mouse to expose the flyout so we can see the text
            self._move_to_complete_theme_flyout()
            if not self.is_flyout_visible:
                raise Exception('Flyout did not expand, possible mouse focus/ActionChain issue')
            return self._root_element.find_element(*self._not_available_locator).text

        @property
        def is_incompatible_flag_visible(self):
            # This refers to the grey 'This complete theme is incompatible' text on the panel

            from selenium.common.exceptions import NoSuchElementException
            self.selenium.implicitly_wait(0)
            try:
                return self._root_element.find_element(*self._is_incompatible_locator).is_displayed()
            except NoSuchElementException:
                return False
            finally:
                # set back to where you once belonged
                self.selenium.implicitly_wait(self.testsetup.default_implicit_wait)


class CompleteTheme(Base):

    _addon_title = (By.CSS_SELECTOR, "h1.addon")
    _install_button = (By.CSS_SELECTOR, "p.install-button > a")
    _breadcrumb_locator = (By.ID, "breadcrumbs")

    @property
    def addon_title(self):
        return self.selenium.find_element(*self._addon_title).text

    @property
    def install_button_exists(self):
        return self.is_element_visible(*self._install_button)

    @property
    def breadcrumb(self):
        return self.selenium.find_element(*self._breadcrumb_locator).text


class CompleteThemesCategory(Base):

    _title_locator = (By.CSS_SELECTOR, "section.primary > h1")
    _breadcrumb_locator = (By.CSS_SELECTOR, "#breadcrumbs > ol")

    @property
    def title(self):
        return self.selenium.find_element(*self._title_locator).text


class CompleteThemesSearchResultList(SearchResultList):
    _results_locator = (By.CSS_SELECTOR, '.items .item')

    class CompleteThemesSearchResultItem(SearchResultList.SearchResultItem):
        _name_locator = (By.CSS_SELECTOR, 'h3 > a')

########NEW FILE########
__FILENAME__ = details
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re

from urllib2 import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains

from pages.page import Page
from pages.desktop.base import Base


class Details(Base):

    _breadcrumb_locator = (By.ID, "breadcrumbs")

    # addon informations
    _title_locator = (By.CSS_SELECTOR, 'hgroup .addon')
    _version_number_locator = (By.CSS_SELECTOR, "span.version-number")
    _no_restart_locator = (By.CSS_SELECTOR, "span.no-restart")
    _authors_locator = (By.XPATH, "//h4[@class='author']/a")
    _summary_locator = (By.ID, "addon-summary")
    _install_button_locator = (By.CSS_SELECTOR, '.button.prominent.add.installer')
    _install_button_attribute_locator = (By.CSS_SELECTOR, '.install-wrapper .install-shell .install.clickHijack')
    _rating_locator = (By.CSS_SELECTOR, "span.stars.large")
    _license_link_locator = (By.CSS_SELECTOR, ".source-license > a")
    _whats_this_license_locator = (By.CSS_SELECTOR, "a.license-faq")
    _view_the_source_locator = (By.CSS_SELECTOR, "a.source-code")
    _complete_version_history_locator = (By.CSS_SELECTOR, "p.more > a")
    _description_locator = (By.CSS_SELECTOR, "div.prose")
    _other_applications_locator = (By.ID, "other-apps")
    _compatibility_locator = (By.CSS_SELECTOR, '.meta.compat')
    _review_link_locator = (By.ID, 'reviews-link')
    _daily_users_link_locator = (By.CSS_SELECTOR, '#daily-users > a.stats')

    _about_addon_locator = (By.CSS_SELECTOR, "section.primary > h2")
    _version_information_locator = (By.ID, "detail-relnotes")
    _version_information_heading_locator = (By.CSS_SELECTOR, "#detail-relnotes > h2")
    _version_information_heading_link_locator = (By.CSS_SELECTOR, "#detail-relnotes > h2 > a")
    _version_information_button_locator = (By.CSS_SELECTOR, "#detail-relnotes > h2 > a > b")
    _version_information_content_locator = (By.CSS_SELECTOR, "#detail-relnotes > div.content")
    _release_version_locator = (By.CSS_SELECTOR, "div.info > h3 > a")
    _source_code_license_information_locator = (By.CSS_SELECTOR, ".source > li > a")
    _reviews_title_locator = (By.CSS_SELECTOR, "#reviews > h2")
    _tags_locator = (By.ID, "tagbox")
    _other_addons_header_locator = (By.CSS_SELECTOR, "h2.compact-bottom")
    _other_addons_list_locator = (By.CSS_SELECTOR, ".primary .listing-grid")
    _part_of_collections_header_locator = (By.CSS_SELECTOR, "#collections-grid h2")
    _part_of_collections_list_locator = (By.CSS_SELECTOR, "#collections-grid section li")
    _icon_locator = (By.CSS_SELECTOR, "img.icon")
    _support_link_locator = (By.CSS_SELECTOR, "a.support")
    _review_details_locator = (By.CSS_SELECTOR, ".review .description")
    _all_reviews_link_locator = (By.CSS_SELECTOR, "#reviews a.more-info")
    _review_locator = (By.CSS_SELECTOR, "#reviews > div.review:not(.reply)")
    _info_link_locator = (By.CSS_SELECTOR, "li > a.scrollto")
    _rating_counter_locator = (By.CSS_SELECTOR, ".grouped_ratings .num_ratings")

    _devs_comments_section_locator = (By.CSS_SELECTOR, "#developer-comments")
    _devs_comments_title_locator = (By.CSS_SELECTOR, "#developer-comments h2")
    _devs_comments_toggle_locator = (By.CSS_SELECTOR, "#developer-comments h2 a")
    _devs_comments_message_locator = (By.CSS_SELECTOR, "#developer-comments div.content")

    #more about this addon
    _website_locator = (By.CSS_SELECTOR, ".links a.home")
    #other_addons
    _other_addons_by_author_locator = (By.CSS_SELECTOR, "#author-addons > ul.listing-grid > section li > div.addon")
    _other_addons_by_author_text_locator = (By.CSS_SELECTOR, '#author-addons > h2')
    _reviews_section_header_locator = (By.CSS_SELECTOR, '#reviews > h2')
    _reviews_locator = (By.CSS_SELECTOR, "section#reviews div")
    _add_review_link_locator = (By.ID, "add-review")

    _add_to_collection_locator = (By.CSS_SELECTOR, ".collection-add.widget.collection")
    _add_to_collection_widget_button_locator = (By.CSS_SELECTOR, ".collection-add-login .register-button .button")
    _add_to_collection_widget_login_link_locator = (By.CSS_SELECTOR, "div.collection-add-login p:nth-child(3) > a")
    _add_to_favorites_widget_locator = (By.CSS_SELECTOR, 'div.widgets > a.favorite')

    _development_channel_content_locator = (By.CSS_SELECTOR, '.content > p')
    _development_channel_locator = (By.CSS_SELECTOR, "#beta-channel")
    _development_channel_toggle = (By.CSS_SELECTOR, '#beta-channel a.toggle')
    _development_channel_install_button_locator = (By.CSS_SELECTOR, '#beta-channel p.install-button a.button.caution')
    _development_channel_title_locator = (By.CSS_SELECTOR, "#beta-channel h2")
    _development_channel_content_locator = (By.CSS_SELECTOR, "#beta-channel > div.content")
    _development_version_locator = (By.CSS_SELECTOR, '.beta-version')

    _add_to_favorites_updating_locator = (By.CSS_SELECTOR, "a.ajax-loading")

    # contribute to addon
    _contribute_button_locator = (By.ID, 'contribute-button')
    _paypal_login_dialog_locator = (By.CSS_SELECTOR, '#page .content')

    def __init__(self, testsetup, addon_name=None):
        #formats name for url
        Base.__init__(self, testsetup)
        if (addon_name is not None):
            self.addon_name = addon_name.replace(" ", "-")
            self.addon_name = re.sub(r'[^A-Za-z0-9\-]', '', self.addon_name).lower()
            self.addon_name = self.addon_name[:27]
            self.selenium.get("%s/addon/%s" % (self.base_url, self.addon_name))
        WebDriverWait(self.selenium, self.timeout).until(
            lambda s: self.is_element_visible(*self._title_locator))

    @property
    def _page_title(self):
        return "%s :: Add-ons for Firefox" % self.title

    @property
    def title(self):
        base = self.selenium.find_element(*self._title_locator).text
        '''base = "firebug 1.8.9" we will have to remove version number for it'''
        if "Themes" in self.selenium.find_element(*self._breadcrumb_locator).text:
            return base
        else:
            return base.replace(self.version_number, '').replace(self.no_restart, '').strip()

    @property
    def no_restart(self):
        if self.is_element_present(*self._no_restart_locator):
            return self.selenium.find_element(*self._no_restart_locator).text
        else:
            return ""

    @property
    def has_reviews(self):
        return self.review_count > 0

    def click_all_reviews_link(self):
        self.selenium.find_element(*self._all_reviews_link_locator).click()

        from pages.desktop.addons_site import ViewReviews
        return ViewReviews(self.testsetup)

    @property
    def review_count(self):
        return len(self.selenium.find_elements(*self._review_locator))

    @property
    def total_reviews_count(self):
        text = self.selenium.find_element(*self._review_link_locator).text
        return int(text.split()[0].replace(',', ''))

    def click_view_statistics(self):
        self.selenium.find_element(*self._daily_users_link_locator).click()
        from pages.desktop.statistics import Statistics
        stats_page = Statistics(self.testsetup)
        WebDriverWait(self.selenium, self.timeout).until(lambda s: stats_page.is_chart_loaded)
        return stats_page

    @property
    def daily_users_number(self):
        text = self.selenium.find_element(*self._daily_users_link_locator).text
        return int(text.split()[0].replace(',', ''))

    @property
    def breadcrumb(self):
        return self.selenium.find_element(*self._breadcrumb_locator).text

    @property
    def version_number(self):
        return self.selenium.find_element(*self._version_number_locator).text

    @property
    def source_code_license_information(self):
        return self.selenium.find_element(*self._source_code_license_information_locator).text

    @property
    def authors(self):
        return [element.text for element in self.selenium.find_elements(*self._authors_locator)]

    @property
    def summary(self):
        return self.selenium.find_element(*self._summary_locator).text

    @property
    def rating(self):
        return re.findall("\d", self.selenium.find_element(*self._rating_locator).text)[0]

    def click_whats_this_license(self):
        self.selenium.find_element(*self._whats_this_license_locator).click()
        from pages.desktop.addons_site import UserFAQ
        return UserFAQ(self.testsetup)

    @property
    def license_site(self):
        return self.selenium.find_element(*self._license_link_locator).get_attribute('href')

    @property
    def license_link_text(self):
        return self.selenium.find_element(*self._license_link_locator).text

    @property
    def description(self):
        return self.selenium.find_element(*self._description_locator).text

    @property
    def other_apps(self):
        return self.selenium.find_element(*self._other_applications_locator).text

    @property
    def version_information_heading(self):
        return self.selenium.find_element(*self._version_information_heading_locator).text

    @property
    def version_information_href(self):
        return self.selenium.find_element(*self._version_information_heading_link_locator).get_attribute('href')

    @property
    def release_version(self):
        return self.selenium.find_element(*self._release_version_locator).text

    @property
    def about_addon(self):
        return self.selenium.find_element(*self._about_addon_locator).text

    @property
    def review_title(self):
        return self.selenium.find_element(*self._reviews_title_locator).text

    @property
    def review_details(self):
        return [review.text for review in self.selenium.find_elements(*self._review_details_locator)]

    @property
    def often_used_with_header(self):
        return self.selenium.find_element(*self._other_addons_header_locator).text

    @property
    def devs_comments_title(self):
        return self.selenium.find_element(*self._devs_comments_title_locator).text

    @property
    def devs_comments_message(self):
        return self.selenium.find_element(*self._devs_comments_message_locator).text

    @property
    def compatible_applications(self):
        return self.selenium.find_element(*self._compatibility_locator).text

    @property
    def is_version_information_install_button_visible(self):
        return self.is_element_visible(*self._install_button_locator)

    def click_and_hold_install_button_returns_class_value(self):
        click_element = self.selenium.find_element(*self._install_button_locator)
        ActionChains(self.selenium).\
            click_and_hold(click_element).\
            perform()
        return self.selenium.find_element(*self._install_button_attribute_locator).get_attribute("class")

    @property
    def is_whats_this_license_visible(self):
        return self.is_element_visible(*self._whats_this_license_locator)

    @property
    def license_faq_text(self):
        return self.selenium.find_element(*self._whats_this_license_locator).text

    @property
    def is_source_code_license_information_visible(self):
        return self.is_element_visible(*self._source_code_license_information_locator)

    @property
    def is_view_the_source_link_visible(self):
        return self.is_element_visible(*self._view_the_source_locator)

    def click_view_source_code(self):
        self.selenium.find_element(*self._view_the_source_locator).click()
        from pages.desktop.addons_site import ViewAddonSource
        addon_source = ViewAddonSource(self.testsetup)
        WebDriverWait(self.selenium, self.timeout).until(lambda s: addon_source.is_file_viewer_visible)
        return addon_source

    @property
    def view_source_code_text(self):
        return self.selenium.find_element(*self._view_the_source_locator).text

    @property
    def is_complete_version_history_visible(self):
        return self.is_element_visible(*self._complete_version_history_locator)

    @property
    def is_version_information_section_in_view(self):
        """ Check if the information section is in view.

        The script returns the pixels the current document has been scrolled from the
        upper left corner of the window, vertically.
        If the offset is > 1000, the page has scrolled to the information section and it
        is in view.
        """
        return (self.selenium.execute_script('return window.pageYOffset')) > 1000

    @property
    def is_often_used_with_list_visible(self):
        return self.is_element_visible(*self._other_addons_list_locator)

    @property
    def are_tags_visible(self):
        return self.is_element_visible(*self._tags_locator)

    @property
    def is_devs_comments_section_present(self):
        return self.is_element_present(*self._devs_comments_section_locator)

    @property
    def is_devs_comments_section_expanded(self):
        return self.is_element_visible(*self._devs_comments_message_locator)

    @property
    def part_of_collections_header(self):
        return self.selenium.find_element(*self._part_of_collections_header_locator).text

    @property
    def part_of_collections(self):
        return [self.PartOfCollectionsSnippet(self.testsetup, web_element)
                for web_element in self.selenium.find_elements(*self._part_of_collections_list_locator)]

    @property
    def is_reviews_section_in_view(self):
        return self.selenium.execute_script('return window.pageYOffset') > 1000

    @property
    def is_reviews_section_visible(self):
        return self.is_element_visible(*self._reviews_section_header_locator)

    class PartOfCollectionsSnippet(Page):

        _name_locator = (By.CSS_SELECTOR, 'div.summary > h3')

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        def click_collection(self):
            self._root_element.find_element(*self._name_locator).click()
            from pages.desktop.collections import Collections
            return Collections(self.testsetup)

        @property
        def name(self):
            return self._root_element.find_element(*self._name_locator).text

    def click_other_apps(self):
        self.selenium.find_element(*self._other_applications_locator).click()

    @property
    def icon_url(self):
        return self.selenium.find_element(*self._icon_locator).get_attribute('src')

    @property
    def website(self):
        url = self.selenium.find_element(*self._website_locator).get_attribute('href')
        return self._extract_url_from_link(url)

    def click_website_link(self):
        self.selenium.find_element(*self._website_locator).click()
        WebDriverWait(self.selenium, self.timeout).until(lambda s: self.selenium.title)

    @property
    def support_url(self):
        support_url = self.selenium.find_element(*self._support_link_locator).get_attribute('href')
        match = re.findall("http", support_url)
        #staging url
        if len(match) > 1:
            return self._extract_url_from_link(support_url)
        #production url
        else:
            return support_url

    def _extract_url_from_link(self, url):
        #parses out extra certificate stuff from urls in staging only
        return urlparse.unquote(re.search('\w+://.*/(\w+%3A//.*)', url).group(1))

    @property
    def other_addons_by_authors_text(self):
        return self.selenium.find_element(*self._other_addons_by_author_text_locator).text

    @property
    def other_addons(self):
        return [self.OtherAddons(self.testsetup, other_addon_web_element)
                for other_addon_web_element in self.selenium.find_elements(*self._other_addons_by_author_locator)]

    @property
    def previewer(self):
        return self.ImagePreviewer(self.testsetup)

    def click_add_to_collection_widget(self):
        self.selenium.find_element(*self._add_to_collection_locator).click()

    @property
    def collection_widget_button(self):
        return self.selenium.find_element(*self._add_to_collection_widget_button_locator).text

    @property
    def collection_widget_login_link(self):
        return self.selenium.find_element(*self._add_to_collection_widget_login_link_locator).text

    class ImagePreviewer(Page):

        #navigation
        _next_locator = (By.CSS_SELECTOR, 'section.previews div.carousel > a.next')
        _prev_locator = (By.CSS_SELECTOR, 'section.previews div.carousel > a.prev')

        _image_locator = (By.CSS_SELECTOR, '#preview li')
        _link_locator = (By.TAG_NAME, 'a')

        def next_set(self):
            self.selenium.find_element(*self._next_locator).click()

        def prev_set(self):
            self.selenium.find_element(*self._prev_locator).click()

        def click_image(self, image_no=0):
            images = self.selenium.find_elements(*self._image_locator)
            images[image_no].find_element(*self._link_locator).click()

            from pages.desktop.regions.image_viewer import ImageViewer
            image_viewer = ImageViewer(self.testsetup)
            WebDriverWait(self.selenium, self.timeout).until(lambda s: image_viewer.is_visible)
            return image_viewer

        def image_title(self, image_no):
            return self.selenium.find_element(
                self._image_locator[0],
                '%s:nth-child(%s) a' % (self._image_locator[1], image_no + 1)
            ).get_attribute('title')

        def image_link(self, image_no):
            return self.selenium.find_element(
                self._image_locator[0],
                '%s:nth-child(%s) a img' % (self._image_locator[1], image_no + 1)
            ).get_attribute('src')

        @property
        def image_count(self):
            return len(self.selenium.find_elements(*self._image_locator))

        @property
        def image_set_count(self):
            if self.image_count % 3 == 0:
                return self.image_count / 3
            else:
                return self.image_count / 3 + 1

    def review(self, element):
        return self.DetailsReviewSnippet(self.testsetup, element)

    @property
    def reviews(self):
        return [self.DetailsReviewSnippet(self.testsetup, web_element)
                for web_element in self.selenium.find_elements(*self._reviews_locator)]

    @property
    def version_info_link(self):
        return self.selenium.find_element(*self._info_link_locator).get_attribute('href')

    def click_version_info_link(self):
        self.selenium.find_element(*self._info_link_locator).click()

    def click_user_reviews_link(self):
        self.selenium.find_element(*self._review_link_locator).click()
        WebDriverWait(self.selenium, self.timeout).until(lambda s: (self.selenium.execute_script('return window.pageYOffset')) > 1000)

    def expand_version_information(self):
        self.selenium.find_element(*self._version_information_button_locator).click()
        WebDriverWait(self.selenium, self.timeout).until(
            lambda s: self.is_version_information_section_expanded)

    @property
    def is_version_information_section_expanded(self):
        return self.is_element_visible(*self._version_information_content_locator)

    def expand_devs_comments(self):
        self.selenium.find_element(*self._devs_comments_toggle_locator).click()
        WebDriverWait(self.selenium, self.timeout).until(
            lambda s: self.is_devs_comments_section_expanded)

    class OtherAddons(Page):

        _name_locator = (By.CSS_SELECTOR, 'div.summary h3')

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        @property
        def name(self):
            return self._root_element.find_element(*self._name_locator).text

        def click_addon_link(self):
            self._root_element.find_element(*self._name_locator).click()

    class DetailsReviewSnippet(Page):

        _reviews_locator = (By.CSS_SELECTOR, '#reviews div')  # Base locator
        _username_locator = (By.CSS_SELECTOR, 'p.byline a')

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        @property
        def username(self):
            return self._root_element.find_element(*self._username_locator).text

        def click_username(self):
            self._root_element.find_element(*self._username_locator).click()
            from pages.desktop.user import User
            return User(self.testsetup)

    def click_to_write_review(self):
        self.selenium.find_element(*self._add_review_link_locator).click()
        from pages.desktop.addons_site import WriteReviewBlock
        return WriteReviewBlock(self.testsetup)

    @property
    def development_channel_text(self):
        return self.selenium.find_element(*self._development_channel_title_locator).text

    def click_development_channel(self):
        expander = self.selenium.find_element(*self._development_channel_toggle)
        expander_saved_class = expander.get_attribute('class')
        self.selenium.find_element(*self._development_channel_toggle).click()
        WebDriverWait(self.selenium, self.timeout).until(lambda s: expander.get_attribute('class') is not expander_saved_class)

    @property
    def is_development_channel_expanded(self):
        is_expanded = self.selenium.find_element(*self._development_channel_locator).get_attribute('class')
        return "expanded" in is_expanded

    @property
    def is_development_channel_install_button_visible(self):
        WebDriverWait(self.selenium, self.timeout).until(
            lambda s: self.is_element_visible(*self._development_channel_install_button_locator),
            "Timeout waiting for 'development channel install' button.")
        return True

    @property
    def development_channel_content(self):
        return self.selenium.find_element(*self._development_channel_content_locator).text

    @property
    def beta_version(self):
        return self.selenium.find_element(*self._development_version_locator).text

    class ContributionSnippet(Page):

        _make_contribution_button_locator = (By.ID, 'contribute-confirm')

        def __init__(self, testsetup):
            Page.__init__(self, testsetup)

            WebDriverWait(self.selenium, self.timeout).until(
                lambda s: s.find_element(*self._make_contribution_button_locator).is_displayed(),
                "Timeout waiting for 'make contribution' button.")

        def click_make_contribution_button(self):
            self.selenium.maximize_window()
            self.selenium.find_element(*self._make_contribution_button_locator).click()
            from pages.desktop.regions.paypal_frame import PayPalFrame
            return PayPalFrame(self.testsetup)

        @property
        def is_make_contribution_button_visible(self):
            return self.is_element_visible(*self._make_contribution_button_locator)

        @property
        def make_contribution_button_name(self):
            return self.selenium.find_element(*self._make_contribution_button_locator).text

    def click_contribute_button(self):
        self.selenium.find_element(*self._contribute_button_locator).click()
        return self.ContributionSnippet(self.testsetup)

    @property
    def is_paypal_login_dialog_visible(self):
        return self.is_element_visible(*self._paypal_login_dialog_locator)

    def _wait_for_favorite_addon_to_be_added(self):
        WebDriverWait(self.selenium, self.timeout).until(lambda s: not self.is_element_present(*self._add_to_favorites_updating_locator))

    def click_add_to_favorites(self):
        self.selenium.find_element(*self._add_to_favorites_widget_locator).click()
        self._wait_for_favorite_addon_to_be_added()

    @property
    def is_addon_marked_as_favorite(self):
        is_favorite = self.selenium.find_element(*self._add_to_favorites_widget_locator).text
        return 'Remove from favorites' in is_favorite

    @property
    def total_review_count(self):
        return self.selenium.find_element(*self._total_review_count_locator).text

########NEW FILE########
__FILENAME__ = discovery
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from pages.page import Page
from pages.desktop.base import Base


class DiscoveryPane(Base):

    _what_are_addons_text_locator = (By.CSS_SELECTOR, '#intro p')
    _mission_section_text_locator = (By.CSS_SELECTOR, '#mission > p')
    _learn_more_locator = (By.ID, 'learn-more')
    _mozilla_org_link_locator = (By.CSS_SELECTOR, '#mission a')
    _download_count_text_locator = (By.ID, 'download-count')
    _themes_section_locator = (By.ID, 'featured-themes')
    _themes_see_all_link = (By.CSS_SELECTOR, ".all[href='/en-US/firefox/themes/']")
    _themes_locator = (By.CSS_SELECTOR, '#featured-themes ul li')
    _themes_link_locator = (By.CSS_SELECTOR, '#featured-themes ul a')
    _more_ways_section_locator = (By.ID, 'more-ways')
    _more_ways_addons_locator = (By.ID, 'more-addons')
    _more_ways_complete_themes_locator = (By.ID, 'more-complete-themes')
    _up_and_coming_item = (By.XPATH, "//section[@id='up-and-coming']/ul/li/a[@class='addon-title']")
    _logout_link_locator = (By.CSS_SELECTOR, '#logout > a')

    _carousel_panels_locator = (By.CSS_SELECTOR, '#promos .slider li.panel')
    _carousel_next_panel_button_locator = (By.CSS_SELECTOR, '#nav-features .nav-next a')
    _carousel_previous_panel_button_locator = (By.CSS_SELECTOR, '#nav-features .nav-prev a')

    _featured_addons_base_locator = (By.CSS_SELECTOR, '#featured-addons .addon-title ')

    def __init__(self, testsetup, path):
        Base.__init__(self, testsetup)
        self.selenium.get(self.base_url + path)
        #resizing this page for elements that disappear when the window is < 1000
        #self.selenium.set_window_size(1000, 1000) Commented because this selenium call is still in beta

    @property
    def what_are_addons_text(self):
        return self.selenium.find_element(*self._what_are_addons_text_locator).text

    def click_learn_more(self):
        self.selenium.find_element(*self._learn_more_locator).click()

    @property
    def mission_section(self):
        return self.selenium.find_element(*self._mission_section_text_locator).text

    def mozilla_org_link_visible(self):
        return self.is_element_visible(*self._mozilla_org_link_locator)

    @property
    def download_count(self):
        return self.selenium.find_element(*self._download_count_text_locator).text

    @property
    def is_themes_section_visible(self):
        return self.is_element_visible(*self._themes_section_locator)

    @property
    def themes_count(self):
        return len(self.selenium.find_elements(*self._themes_locator))

    @property
    def is_themes_see_all_link_visible(self):
        return self.is_element_visible(*self._themes_see_all_link)

    @property
    def first_theme(self):
        return self.selenium.find_elements(*self._themes_locator)[0].text

    def click_on_first_theme(self):
        self.selenium.find_element(*self._themes_link_locator).click()
        return DiscoveryThemesDetail(self.testsetup)

    @property
    def more_ways_section_visible(self):
        return self.is_element_visible(*self._more_ways_section_locator)

    @property
    def browse_all_addons(self):
        return self.selenium.find_element(*self._more_ways_addons_locator).text

    @property
    def see_all_complete_themes(self):
        return self.selenium.find_element(*self._more_ways_complete_themes_locator).text

    @property
    def up_and_coming_item_count(self):
        return len(self.selenium.find_elements(*self._up_and_coming_item))

    def click_logout(self):
        self.selenium.find_element(*self._logout_link_locator).click()
        from pages.desktop.home import Home
        return Home(self.testsetup, open_url=False)

    @property
    def carousel_panels(self):
        return [self.CarouselPanelRegion(self.testsetup, element)
                for element in self.selenium.find_elements(*self._carousel_panels_locator)]

    def show_next_carousel_panel(self):
        self.selenium.find_element(*self._carousel_next_panel_button_locator).click()

    def show_previous_carousel_panel(self):
        self.selenium.find_element(*self._carousel_previous_panel_button_locator).click()

    class CarouselPanelRegion(Page):

        _heading_locator = (By.CSS_SELECTOR, 'h2')

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        @property
        def heading(self):
            return self._root_element.find_element(*self._heading_locator).text

        @property
        def is_visible(self):
            return self._root_element.is_displayed()

        def wait_for_next_promo(self):
            WebDriverWait(self.selenium, self.timeout).until(lambda s:
                                                         self._root_element.find_element(*self._heading_locator).is_displayed())


class DiscoveryThemesDetail(Base):

    _theme_title = (By.CSS_SELECTOR, 'h1.addon')

    @property
    def theme_title(self):
        return self.selenium.find_element(*self._theme_title).text

########NEW FILE########
__FILENAME__ = extensions
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from time import strptime, mktime

from selenium.webdriver.common.by import By

from pages.page import Page
from pages.desktop.base import Base


class ExtensionsHome(Base):

    _page_title = 'Featured Extensions :: Add-ons for Firefox'
    _extensions_locator = (By.CSS_SELECTOR, "div.items div.item.addon")
    _default_selected_tab_locator = (By.CSS_SELECTOR, "#sorter li.selected")
    _subscribe_link_locator = (By.CSS_SELECTOR, "a#subscribe")
    _featured_extensions_header_locator = (By.CSS_SELECTOR, "#page > .primary > h1")
    _paginator_locator = (By.CSS_SELECTOR, ".paginator.c.pjax-trigger")

    @property
    def extensions(self):
        return [Extension(self.testsetup, web_element)
                for web_element in self.selenium.find_elements(*self._extensions_locator)]

    @property
    def subscribe_link_text(self):
        return self.selenium.find_element(*self._subscribe_link_locator).text

    @property
    def featured_extensions_header_text(self):
        return self.selenium.find_element(*self._featured_extensions_header_locator).text

    @property
    def sorter(self):
        from pages.desktop.regions.sorter import Sorter
        return Sorter(self.testsetup)

    @property
    def paginator(self):
        from pages.desktop.regions.paginator import Paginator
        return Paginator(self.testsetup)

    @property
    def is_paginator_present(self):
        return self.is_element_present(*self._paginator_locator)


class Extension(Page):
        _name_locator = (By.CSS_SELECTOR, "h3 a")
        _updated_date = (By.CSS_SELECTOR, 'div.info > div.vitals > div.updated')
        _featured_locator = (By.CSS_SELECTOR, 'div.info > h3 > span.featured')
        _user_count_locator = (By.CSS_SELECTOR, 'div.adu')

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        @property
        def featured(self):
            return self._root_element.find_element(*self._featured_locator).text

        @property
        def name(self):
            return self._root_element.find_element(*self._name_locator).text

        @property
        def user_count(self):
            return int(self._root_element.find_element(*self._user_count_locator).text.strip('user').replace(',', '').rstrip())

        def click(self):
            self._root_element.find_element(*self._name_locator).click()
            from pages.desktop.details import Details
            return Details(self.testsetup)

        @property
        def added_date(self):
            """Returns updated date of result in POSIX format."""
            date = self._root_element.find_element(*self._updated_date).text.replace('Added ', '')
            # convert to POSIX format
            date = strptime(date, '%B %d, %Y')
            return mktime(date)

        @property
        def updated_date(self):
            """Returns updated date of result in POSIX format."""
            date = self._root_element.find_element(*self._updated_date).text.replace('Updated ', '')
            # convert to POSIX format
            date = strptime(date, '%B %d, %Y')
            return mktime(date)

########NEW FILE########
__FILENAME__ = home
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait

from pages.page import Page
from pages.desktop.base import Base


class Home(Base):

    _page_title = "Add-ons for Firefox"
    _first_addon_locator = (By.CSS_SELECTOR, ".summary > a > h3")
    _other_applications_link_locator = (By.ID, "other-apps")

    #Most Popular List
    _most_popular_item_locator = (By.CSS_SELECTOR, "ol.toplist li")
    _most_popular_list_heading_locator = (By.CSS_SELECTOR, "#homepage > .secondary h2")

    _explore_side_navigation_header_locator = (By.CSS_SELECTOR, "#side-nav > h2:nth-child(1)")
    _explore_featured_link_locator = (By.CSS_SELECTOR, "#side-nav .s-featured a")
    _explore_popular_link_locator = (By.CSS_SELECTOR, "#side-nav .s-users a")
    _explore_top_rated_link_locator = (By.CSS_SELECTOR, "#side-nav .s-rating a")

    _featured_themes_see_all_link = (By.CSS_SELECTOR, "#featured-themes h2 a")
    _featured_themes_title_locator = (By.CSS_SELECTOR, "#featured-themes h2")
    _featured_themes_items_locator = (By.CSS_SELECTOR, "#featured-themes li")

    _featured_collections_locator = (By.CSS_SELECTOR, "#featured-collections h2")
    _featured_collections_elements_locator = (By.CSS_SELECTOR, "#featured-collections section:nth-child(1) li")

    _featured_extensions_title_locator = (By.CSS_SELECTOR, '#featured-extensions > h2')
    _featured_extensions_see_all_locator = (By.CSS_SELECTOR, '#featured-extensions > h2 > a')
    _featured_extensions_elements_locator = (By.CSS_SELECTOR, '#featured-extensions section:nth-child(1) > li > div')

    _extensions_menu_link = (By.CSS_SELECTOR, "#extensions > a")

    _promo_box_locator = (By.ID, "promos")

    _up_and_coming_locator = (By.ID, "upandcoming")

    def __init__(self, testsetup, open_url=True):
        """Creates a new instance of the class and gets the page ready for testing."""
        Base.__init__(self, testsetup)
        if open_url:
            self.selenium.get(self.base_url)
        WebDriverWait(self.selenium, self.timeout).until(lambda s: s.find_element(*self._promo_box_locator).size['height'] == 271)

    def hover_over_addons_home_title(self):
        home_item = self.selenium.find_element(*self._amo_logo_link_locator)
        ActionChains(self.selenium).\
            move_to_element(home_item).\
            perform()

    def click_featured_themes_see_all_link(self):
        self.selenium.find_element(*self._featured_themes_see_all_link).click()
        from pages.desktop.themes import Themes
        return Themes(self.testsetup)

    def click_featured_collections_see_all_link(self):
        self.selenium.find_element(*self._featured_collections_locator).find_element(By.CSS_SELECTOR, " a").click()
        from pages.desktop.collections import Collections
        return Collections(self.testsetup)

    def click_to_explore(self, what):
        what = what.replace(' ', '_').lower()
        self.selenium.find_element(*getattr(self, "_explore_%s_link_locator" % what)).click()
        from pages.desktop.extensions import ExtensionsHome
        return ExtensionsHome(self.testsetup)

    def get_category(self):
        from pages.desktop.category import Category
        return Category(self.testsetup)

    @property
    def most_popular_count(self):
        return len(self.selenium.find_elements(*self._most_popular_item_locator))

    @property
    def most_popular_list_heading(self):
        return self.selenium.find_element(*self._most_popular_list_heading_locator).text

    @property
    def featured_themes_count(self):
        return len(self.selenium.find_elements(*self._featured_themes_items_locator))

    @property
    def featured_themes_title(self):
        return self.selenium.find_element(*self._featured_themes_title_locator).text

    @property
    def featured_collections_title(self):
        return self.selenium.find_element(*self._featured_collections_locator).text

    @property
    def featured_collections_count(self):
        return len(self.selenium.find_elements(*self._featured_collections_elements_locator))

    @property
    def featured_extensions_see_all(self):
        return self.selenium.find_element(*self._featured_extensions_see_all_locator).text

    @property
    def featured_extensions_title(self):
        title = self.selenium.find_element(*self._featured_extensions_title_locator).text
        return title.replace(self.featured_extensions_see_all, '').strip()

    @property
    def featured_extensions_count(self):
        return len(self.selenium.find_elements(*self._featured_extensions_elements_locator))

    @property
    def up_and_coming_island(self):
        from pages.desktop.regions.island import Island
        return Island(self.testsetup, self.selenium.find_element(*self._up_and_coming_locator))

    @property
    def explore_side_navigation_header_text(self):
        return self.selenium.find_element(*self._explore_side_navigation_header_locator).text

    @property
    def explore_featured_link_text(self):
        return self.selenium.find_element(*self._explore_featured_link_locator).text

    @property
    def explore_popular_link_text(self):
        return self.selenium.find_element(*self._explore_popular_link_locator).text

    @property
    def explore_top_rated_link_text(self):
        return self.selenium.find_element(*self._explore_top_rated_link_locator).text

    def click_on_first_addon(self):
        self.selenium.find_element(*self._first_addon_locator).click()
        from pages.desktop.details import Details
        return Details(self.testsetup)

    def get_title_of_link(self, name):
        name = name.lower().replace(" ", "_")
        locator = getattr(self, "_%s_link_locator" % name)
        return self.selenium.find_element(*locator).get_attribute('title')

    @property
    def promo_box_present(self):
        return self.is_element_visible(*self._promo_box_locator)

    @property
    def most_popular_items(self):
        return [self.MostPopularRegion(self.testsetup, web_element)
                for web_element in self.selenium.find_elements(*self._most_popular_item_locator)]

    def click_featured_extensions_see_all_link(self):
        self.selenium.find_element(*self._featured_extensions_see_all_locator).click()
        from pages.desktop.extensions import ExtensionsHome
        return ExtensionsHome(self.testsetup)

    class MostPopularRegion(Page):
        _name_locator = (By.TAG_NAME, "span")
        _users_locator = (By.CSS_SELECTOR, "small")

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        @property
        def name(self):
            self._root_element.find_element(*self._name_locator).text

        @property
        def users_number(self):
            users_text = self._root_element.find_element(*self._users_locator).text
            return int(users_text.split(' ')[0].replace(',', ''))

    @property
    def featured_extensions(self):
        return [self.FeaturedExtensions(self.testsetup, web_element)
                for web_element in self.selenium.find_elements(*self._featured_extensions_elements_locator)]

    class FeaturedExtensions(Page):

        _author_locator = (By.CSS_SELECTOR, 'div.addon > div.more > div.byline > a')
        _summary_locator = (By.CSS_SELECTOR, 'div.addon > div.more > .addon-summary')
        _link_locator = (By.CSS_SELECTOR, 'div.addon > .summary')

        def __init__(self, testsetup, web_element):
            Page.__init__(self, testsetup)
            self._root_element = web_element

        @property
        def author_name(self):
            self._move_to_addon_flyout()
            return [element.text for element in self._root_element.find_elements(*self._author_locator)]

        @property
        def summary(self):
            self._move_to_addon_flyout()
            return self._root_element.find_element(*self._summary_locator).text

        def _move_to_addon_flyout(self):
            self.selenium.execute_script("window.scrollTo(0, %s)" % (self._root_element.location['y'] + self._root_element.size['height']))
            ActionChains(self.selenium).\
                move_to_element(self._root_element).\
                perform()

        def click_first_author(self):
            author_item = self.selenium.find_element(*self._author_locator)
            ActionChains(self.selenium).\
                move_to_element(author_item).click().\
                perform()
            from pages.desktop.user import User
            return User(self.testsetup)

########NEW FILE########
__FILENAME__ = paypal_popup
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from pages.page import Page
from selenium.webdriver.common.by import By


class PayPalPopup(Page):

    _pop_up_id = '_popupFlow'
    _email_locator = (By.ID, 'email')
    _password_locator = (By.ID, 'password')
    _login_locator = (By.CSS_SELECTOR, '.buttonGroup #login')  # Bug 769251 - Duplicate ID login in Paypal login sandbox frame
    _log_out_locator = (By.ID, 'logOutLink')

    _pay_button_locator = (By.NAME, '_eventId_submit')
    _order_details_locator = (By.ID, 'order-details')

    def __init__(self, testsetup):
        Page.__init__(self, testsetup)
        self.selenium.switch_to_window(self._pop_up_id)

    def login_paypal(self, user):
        credentials = self.testsetup.credentials[user]
        self.selenium.find_element(*self._email_locator).send_keys(credentials['email'])
        self.selenium.find_element(*self._password_locator).send_keys(credentials['password'])
        self.selenium.find_element(*self._login_locator).click()

    def close_paypal_popup(self):
        self.selenium.find_element(*self._pay_button_locator).click()
        self.selenium.switch_to_window('')

    @property
    def is_user_logged_into_paypal(self):
        return self.is_element_visible(*self._log_out_locator)

    def click_pay(self):
        self.selenium.find_element(*self._pay_button_locator).click()

    @property
    def is_payment_successful(self):
        return self.is_element_visible(*self._order_details_locator)

########NEW FILE########
__FILENAME__ = breadcrumbs
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By

from pages.page import Page


class Breadcrumbs(Page):
    _breadcrumbs_locator = (By.CSS_SELECTOR, "#breadcrumbs li")

    @property
    def breadcrumbs(self):
        return [self.BreadcrumbItem(self.testsetup, breadcrumb_list_item)
                for breadcrumb_list_item in self.selenium.find_elements(*self._breadcrumbs_locator)]

    class BreadcrumbItem(Page):
        _link_locator = (By.CSS_SELECTOR, 'a')

        def __init__(self, testsetup, breadcrumb_list_element):
            Page.__init__(self, testsetup)
            self._root_element = breadcrumb_list_element

        def click(self):
            self._root_element.find_element(*self._link_locator).click()

        @property
        def text(self):
            return self._root_element.text

        @property
        def href_value(self):
            return self._root_element.find_element(*self._link_locator).get_attribute('href')

########NEW FILE########
__FILENAME__ = header_menu
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from pages.page import Page


class HeaderMenu(Page):
    """
    This class access the header area from the top of the AMO pages.desktop.
    To access it just use:
        HeaderMenu(self.testsetup, lookup)
    Where lookup is:
        -the web element coresponding to the menu you want to access
    Ex:
        HeaderMenu(self.testsetup, personas_element) returns the Personas menu
    """

    _menu_items_locator = (By.CSS_SELECTOR, 'ul > li')
    _name_locator = (By.CSS_SELECTOR, 'a')
    _footer_locator = (By.ID, 'footer')
    _complete_themes_locator = (By.CSS_SELECTOR, 'div > a > b')

    def __init__(self, testsetup, element):
        Page.__init__(self, testsetup)
        self._root_element = element

    @property
    def name(self):
        return self._root_element.find_element(*self._name_locator).text

    def click(self):
        name = self.name
        self._root_element.find_element(*self._name_locator).click()

        """This is done because sometimes the header menu drop down remains open so we move the focus to footer to close the menu
        We go to footer because all the menus open a window under them so moving the mouse from down to up will not leave any menu
        open over the desired element"""
        footer_element = self.selenium.find_element(*self._footer_locator)
        ActionChains(self.selenium).move_to_element(footer_element).perform()

        if "EXTENSIONS" in name:
            from pages.desktop.extensions import ExtensionsHome
            return ExtensionsHome(self.testsetup)
        elif "THEMES" in name:
            from pages.desktop.themes import Themes
            return Themes(self.testsetup)
        elif "COLLECTIONS" in name:
            from pages.desktop.collections import Collections
            return Collections(self.testsetup)

    def hover(self):
        element = self._root_element.find_element(*self._name_locator)
        ActionChains(self.selenium).move_to_element(element).perform()

    @property
    def is_menu_dropdown_visible(self):
        dropdown_menu = self._root_element.find_element(*self._menu_items_locator)
        return dropdown_menu.is_displayed()

    @property
    def items(self):
        return [self.HeaderMenuItem(self.testsetup, web_element, self)
                for web_element in self._root_element.find_elements(*self._menu_items_locator)]

    class HeaderMenuItem (Page):

        _name_locator = (By.CSS_SELECTOR, 'a')

        def __init__(self, testsetup, element, menu):
            Page.__init__(self, testsetup)
            self._root_element = element
            self._menu = menu

        @property
        def name(self):
            self._menu.hover()
            return self._root_element.find_element(*self._name_locator).text

        @property
        def is_featured(self):
            return self._root_element.find_element(By.CSS_SELECTOR, '*').tag_name == 'em'

        def click(self):
            menu_name = self._menu.name
            self._menu.hover()
            ActionChains(self.selenium).\
                move_to_element(self._root_element).\
                click().\
                perform()

            if "EXTENSIONS" in menu_name:
                from pages.desktop.extensions import ExtensionsHome
                return ExtensionsHome(self.testsetup)
            elif "THEMES" in menu_name:
                from pages.desktop.themes import Themes
                return Themes(self.testsetup)
            elif "COLLECTIONS" in menu_name:
                from pages.desktop.collections import Collections
                return Collections(self.testsetup)

########NEW FILE########
__FILENAME__ = image_viewer
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from pages.page import Page


class ImageViewer(Page):

    _image_viewer = (By.CSS_SELECTOR, '#lightbox > section')
    #controls
    _next_locator = (By.CSS_SELECTOR, 'div.controls > a.control.next')
    _previous_locator = (By.CSS_SELECTOR, 'div.controls > a.control.prev')
    _caption_locator = (By.CSS_SELECTOR, 'div.caption span')
    _close_locator = (By.CSS_SELECTOR, 'div.content > a.close')

    #content
    _images_locator = (By.CSS_SELECTOR, 'div.content > img')
    _current_image_locator = (By.CSS_SELECTOR, 'div.content > img[style*="opacity: 1"]')

    @property
    def is_visible(self):
        return self.is_element_visible(*self._image_viewer)

    @property
    def images_count(self):
        return len(self.selenium.find_elements(*self._images_locator))

    @property
    def is_next_present(self):
        return 'disabled' not in self.selenium.find_element(*self._next_locator).get_attribute('class')

    @property
    def is_previous_present(self):
        return 'disabled' not in self.selenium.find_element(*self._previous_locator).get_attribute('class')

    @property
    def image_link(self):
        return self.selenium.find_element(*self._current_image_locator).get_attribute('src')

    def click_next(self):
        self.selenium.find_element(*self._next_locator).click()

    def click_previous(self):
        self.selenium.find_element(*self._previous_locator).click()

    def close(self):
        self.selenium.find_element(*self._close_locator).click()
        WebDriverWait(self.selenium, self.timeout).until(lambda s: not self.is_element_visible(*self._image_viewer))

    @property
    def caption(self):
        return self.selenium.find_element(*self._caption_locator).text

########NEW FILE########
__FILENAME__ = island
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from pages.page import Page
from unittestzero import Assert


class Island(Page):
    _pager_locator = (By.CSS_SELECTOR, 'nav.pager')
    _title_locator = (By.CSS_SELECTOR, 'h2')
    _see_all_locator = (By.CSS_SELECTOR, 'h2 > a.seeall')
    _sections_locator = (By.CSS_SELECTOR, 'ul > section')
    _item_locator = (By.CSS_SELECTOR, 'li > div')

    def __init__(self, testsetup, element):
        Page.__init__(self, testsetup)
        self._root = element

    @property
    def pager(self):
        try:
            return self.Pager(self.testsetup, self._root.find_element(*self._pager_locator))
        except NoSuchElementException:
            Assert.fail('Paginator is not available')

    @property
    def see_all_text(self):
        return self._root.find_element(*self._see_all_locator).text

    @property
    def see_all_link(self):
        return self._root.find_element(*self._see_all_locator).get_attribute('href')

    def click_see_all(self):
        see_all_url = self.see_all_link
        self._root.find_element(*self._see_all_locator).click()

        if 'extensions' in see_all_url:
            from pages.desktop.extensions import ExtensionsHome
            return ExtensionsHome(self.testsetup)
        elif 'personas' in see_all_url:
            from pages.desktop.personas import Personas
            return Personas(self.testsetup)
        elif 'collections' in see_all_url:
            from pages.desktop.collections import Collections
            return Collections(self.testsetup)

    @property
    def title(self):
        text = self._root.find_element(*self._title_locator).text
        return text.replace(self.see_all_text, '').strip()

    @property
    def visible_section(self):
        for idx, section in enumerate(self._root.find_elements(*self._sections_locator)):
            if section.is_displayed():
                return idx

    @property
    def addons(self):
        return [self.Addon(self.testsetup, element)
                for element in self._root.find_elements(*self._sections_locator)[self.pager.selected_dot].find_elements(*self._item_locator)]

    class Addon(Page):
        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root = element

    class Pager(Page):
        _next_locator = (By.CSS_SELECTOR, 'a.next')
        _prev_locator = (By.CSS_SELECTOR, 'a.prev')
        _dot_locator = (By.CSS_SELECTOR, 'a.dot')
        _footer_locator = (By.ID, 'footer')

        def __init__(self, testsetup, elment):
            Page.__init__(self, testsetup)
            self._root = elment

        def click_footer(self):
            self.selenium.find_element(*self._footer_locator).click()

        def next(self):
            self.click_footer()
            self._root.find_element(*self._next_locator).click()

        def prev(self):
            self.click_footer()
            self._root.find_element(*self._prev_locator).click()

        @property
        def dot_count(self):
            return len(self._root.find_elements(*self._dot_locator))

        @property
        def selected_dot(self):
            for idx, dot in enumerate(self._root.find_elements(*self._dot_locator)):
                if 'selected' in dot.get_attribute('class'):
                    return idx

        def click_dot(self, idx):
            self._root.find_elements(*self._dot_locator)[idx].click()

########NEW FILE########
__FILENAME__ = paginator
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from pages.page import Page


class Paginator(Page):

    #Numbering
    _page_number_locator = (By.CSS_SELECTOR, 'nav.paginator .num > a:nth-child(1)')
    _total_page_number_locator = (By.CSS_SELECTOR, 'nav.paginator .num > a:nth-child(2)')

    #Navigation
    _first_page_locator = (By.CSS_SELECTOR, 'nav.paginator .rel a:nth-child(1)')
    _prev_locator = (By.CSS_SELECTOR, 'nav.paginator .rel a.prev')
    _next_locator = (By.CSS_SELECTOR, 'nav.paginator .rel a.next')
    _last_page_locator = (By.CSS_SELECTOR, 'nav.paginator .rel a:nth-child(4)')

    #Position
    _start_item_number_locator = (By.CSS_SELECTOR, 'nav.paginator .pos b:nth-child(1)')
    _end_item_number_locator = (By.CSS_SELECTOR, 'nav.paginator .pos b:nth-child(2)')
    _total_item_number = (By.CSS_SELECTOR, 'nav.paginator .pos b:nth-child(3)')

    _updating_locator = (By.CSS_SELECTOR, "div.updating")

    def _wait_for_results_refresh(self):
        # On pages that do not have ajax refresh this wait will have no effect.
        WebDriverWait(self.selenium, self.timeout).until(lambda s: not self.is_element_present(*self._updating_locator))

    @property
    def page_number(self):
        return int(self.selenium.find_element(*self._page_number_locator).text)

    @property
    def total_page_number(self):
        return int(self.selenium.find_element(*self._total_page_number_locator).text)

    def click_first_page(self):
        self.selenium.find_element(*self._first_page_locator).click()
        self._wait_for_results_refresh()

    def click_prev_page(self):
        self.selenium.find_element(*self._prev_locator).click()
        self._wait_for_results_refresh()

    @property
    def is_prev_page_disabled(self):
        return 'disabled' in self.selenium.find_element(*self._prev_locator).get_attribute('class')

    @property
    def is_first_page_disabled(self):
        return 'disabled' in self.selenium.find_element(*self._first_page_locator).get_attribute('class')

    def click_next_page(self):
        self.selenium.find_element(*self._next_locator).click()
        self._wait_for_results_refresh()

    @property
    def is_next_page_disabled(self):
        return 'disabled' in self.selenium.find_element(*self._next_locator).get_attribute('class')

    def click_last_page(self):
        self.selenium.find_element(*self._last_page_locator).click()
        self._wait_for_results_refresh()

    @property
    def is_last_page_disabled(self):
        return 'disabled' in self.selenium.find_element(*self._last_page_locator).get_attribute('class')

    @property
    def start_item(self):
        return int(self.selenium.find_element(*self._start_item_number_locator).text)

    @property
    def end_item(self):
        return int(self.selenium.find_element(*self._end_item_number_locator).text)

    @property
    def total_items(self):
        return int(self.selenium.find_element(*self._total_item_number).text)

########NEW FILE########
__FILENAME__ = paypal_frame
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from pages.page import Page

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class PayPalFrame(Page):

    _iframe_id = 'PPDGFrame'
    _logo_locator = (By.CSS_SELECTOR, '.logo > img')
    _paypal_login_button = (By.CSS_SELECTOR, 'div.logincnt > p > a.button')

    def __init__(self, testsetup):
        Page.__init__(self, testsetup)
        self.selenium.switch_to_frame(self._iframe_id)
        # wait for the paypal logo to appear, then we know the frame's contents has loaded
        WebDriverWait(self.selenium, self.timeout).until(
            lambda s: s.find_element(*self._logo_locator),
            'Timeout waiting for Paypal logo in frame.')

    def login_to_paypal(self, user="paypal"):
        self.selenium.find_element(*self._paypal_login_button).click()

        from pages.desktop.paypal_popup import PayPalPopup
        pop_up = PayPalPopup(self.testsetup)
        pop_up.login_paypal(user)
        return PayPalPopup(self.testsetup)

########NEW FILE########
__FILENAME__ = search_filter
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By

from pages.page import Page


class FilterBase(Page):

    _results_count_tag = (By.CSS_SELECTOR, 'p.cnt b')

    def tag(self, lookup):
        return self.Tag(self.testsetup, lookup)

    @property
    def results_count(self):
        return self.selenium.find_element(*self._results_count_tag).text

    class FilterResults(Page):

        _item_link = (By.CSS_SELECTOR, ' a')
        _all_tags_locator = (By.CSS_SELECTOR, 'li#tag-facets h3')

        def __init__(self, testsetup, lookup):
            Page.__init__(self, testsetup)
            # expand the thing here to represent the proper user action
            is_expanded = self.selenium.find_element(*self._all_tags_locator).get_attribute('class')
            if ('active' not in is_expanded):
                self.selenium.find_element(*self._all_tags_locator).click()
            self._root_element = self.selenium.find_element(self._base_locator[0],
                                    "%s[a[contains(@data-params, '%s')]]" % (self._base_locator[1], lookup))

        @property
        def name(self):
            return self._root_element.text

        @property
        def is_selected(self):
            return "selected" in self._root_element.get_attribute('class')

        def click_tag(self):
            self._root_element.find_element(*self._item_link).click()

    class Tag(FilterResults):
        _base_locator = (By.XPATH, ".//*[@id='tag-facets']/ul/li")

########NEW FILE########
__FILENAME__ = sorter
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains

from pages.page import Page


class Sorter(Page):

    _sort_by_featured_locator = (By.XPATH, "//div[@id='sorter']//li/a[normalize-space(text())='Featured']")
    _sort_by_most_users_locator = (By.XPATH, "//div[@id='sorter']//li/a[normalize-space(text())='Most Users']")
    _sort_by_top_rated_locator = (By.XPATH, "//div[@id='sorter']//li/a[normalize-space(text())='Top Rated']")
    _sort_by_newest_locator = (By.XPATH, "//div[@id='sorter']//li/a[normalize-space(text())='Newest']")

    _sort_by_name_locator = (By.XPATH, "//div[@id='sorter']//li/a[normalize-space(text())='Name']")
    _sort_by_weekly_downloads_locator = (By.XPATH, "//div[@id='sorter']//li/a[normalize-space(text())='Weekly Downloads']")
    _sort_by_recently_updated_locator = (By.XPATH, "//div[@id='sorter']//li/a[normalize-space(text())='Recently Updated']")
    _sort_by_up_and_coming_locator = (By.XPATH, "//div[@id='sorter']//li/a[normalize-space(text())='Up & Coming']")

    _selected_sort_by_locator = (By.CSS_SELECTOR, '#sorter > ul > li.selected a')

    _hover_more_locator = (By.CSS_SELECTOR, "li.extras > a")
    _updating_locator = (By.CSS_SELECTOR, '.updating.tall')
    _footer_locator = (By.ID, 'footer')

    def sort_by(self, type):
        """This is done because sometimes the hover menus remains open so we move the focus to footer to close the menu
        We go to footer because all the menus open a window under them so moving the mouse from down to up will not leave any menu
        open over the desired element"""
        footer_element = self.selenium.find_element(*self._footer_locator)
        ActionChains(self.selenium).move_to_element(footer_element).perform()
        click_element = self.selenium.find_element(*getattr(self, '_sort_by_%s_locator' % type.replace(' ', '_').lower()))
        if type.replace(' ', '_').lower() in ["featured", "most_users", "top_rated", "newest"]:
            click_element.click()
        else:
            hover_element = self.selenium.find_element(*self._hover_more_locator)
            ActionChains(self.selenium).move_to_element(hover_element).\
                move_to_element(click_element).\
                click().perform()
        WebDriverWait(self.selenium, self.timeout).until(lambda s: not self.is_element_present(*self._updating_locator))

    @property
    def sorted_by(self):
        return self.selenium.find_element(*self._selected_sort_by_locator).text

########NEW FILE########
__FILENAME__ = search
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from time import strptime, mktime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from pages.page import Page
from pages.desktop.base import Base


class SearchResultList(Base):

    _number_of_results_found = (By.CSS_SELECTOR, "#search-facets > p")

    _no_results_locator = (By.CSS_SELECTOR, "p.no-results")
    _search_results_title_locator = (By.CSS_SELECTOR, "section.primary > h1")
    _results_locator = (By.CSS_SELECTOR, "div.items div.item.addon")

    def __init__(self, testsetup):
        Base.__init__(self, testsetup)
        try:  # the result could legitimately be zero, but give it time to make sure
            WebDriverWait(self.selenium, self.timeout).until(
                lambda s: len(s.find_elements(*self._results_locator)) > 0
            )
        except Exception:
            pass

    @property
    def is_no_results_present(self):
        return self.is_element_present(*self._no_results_locator)

    @property
    def number_of_results_text(self):
        return self.selenium.find_element(*self._number_of_results_found).text

    @property
    def search_results_title(self):
        return self.selenium.find_element(*self._search_results_title_locator).text

    @property
    def filter(self):
        from pages.desktop.regions.search_filter import FilterBase
        return FilterBase(self.testsetup)

    @property
    def result_count(self):
        return len(self.selenium.find_elements(*self._results_locator))

    def click_sort_by(self, type):
        from pages.desktop.regions.sorter import Sorter
        Sorter(self.testsetup).sort_by(type)

    def result(self, lookup):
        elements = self.selenium.find_elements(*self._results_locator)
        from pages.desktop.collections import Collections, CollectionSearchResultList
        from pages.desktop.themes import ThemesSearchResultList, Themes
        from pages.desktop.complete_themes import CompleteThemes, CompleteThemesSearchResultList
        if isinstance(self, (Collections, CollectionSearchResultList)):
            return self.CollectionsSearchResultItem(self.testsetup, elements[lookup])
        elif isinstance(self, (Themes, ThemesSearchResultList)):
            return self.ThemesSearchResultItem(self.testsetup, elements[lookup])
        elif isinstance(self, (CompleteThemes, CompleteThemesSearchResultList)):
            return self.CompleteThemesSearchResultItem(self.testsetup, elements[lookup])
        else:
            return self.SearchResultItem(self.testsetup, elements[lookup])

    @property
    def results(self):
        elements = self.selenium.find_elements(*self._results_locator)
        return [self.SearchResultItem(self.testsetup, web_element)
                for web_element in elements
                ]

    @property
    def paginator(self):
        from pages.desktop.regions.paginator import Paginator
        return Paginator(self.testsetup)

    class SearchResultItem(Page):
        _name_locator = (By.CSS_SELECTOR, 'div.info > h3 > a')
        _created_date = (By.CSS_SELECTOR, 'div.info > div.vitals > div.updated')
        _sort_criteria = (By.CSS_SELECTOR, 'div.info > div.vitals > div.adu')

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        @property
        def name(self):
            return self._root_element.find_element(*self._name_locator).text

        @property
        def text(self):
            return self._root_element.text

        @property
        def downloads(self):
            number = self._root_element.find_element(*self._sort_criteria).text
            return int(number.split()[0].replace(',', ''))

        @property
        def users(self):
            number = self._root_element.find_element(*self._sort_criteria).text
            return int(number.split()[0].replace(',', ''))

        @property
        def created_date(self):
            """Returns created date of result in POSIX format."""
            date = self._root_element.find_element(*self._created_date).text.strip().replace('Added ', '')
            # convert to POSIX format
            date = strptime(date, '%B %d, %Y')
            return mktime(date)

        @property
        def is_compatible(self):
            return not 'incompatible' in self._root_element.get_attribute('class')

        @property
        def updated_date(self):
            """Returns updated date of result in POSIX format."""
            date = self._root_element.find_element(*self._created_date).text.replace('Updated ', '')
            # convert to POSIX format
            date = strptime(date, '%B %d, %Y')
            return mktime(date)

        def click_result(self):
            self._root_element.find_element(*self._name_locator).click()
            from pages.desktop.collections import Collection, CollectionSearchResultList
            from pages.desktop.themes import ThemesDetail, ThemesSearchResultList
            from pages.desktop.complete_themes import CompleteTheme, CompleteThemesSearchResultList
            from pages.desktop.details import Details
            if isinstance(self, CollectionSearchResultList.CollectionsSearchResultItem):
                return Collection(self.testsetup)
            elif isinstance(self, ThemesSearchResultList.ThemesSearchResultItem):
                return ThemesDetail(self.testsetup)
            elif isinstance(self, CompleteThemesSearchResultList.CompleteThemesSearchResultItem):
                return CompleteTheme(self.testsetup)
            else:
                return Details(self.testsetup)

########NEW FILE########
__FILENAME__ = statistics
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from selenium.webdriver.common.by import By

from pages.desktop.base import Base


class Statistics(Base):

    _title_locator = (By.CSS_SELECTOR, '.addon')
    _total_downloads_locator = (By.CSS_SELECTOR, '.island.two-up div:nth-child(1) a')
    _usage_locator = (By.CSS_SELECTOR, '.island.two-up div:nth-child(2) a')
    _chart_locator = (By.CSS_SELECTOR, '#head-chart > div')
    _no_data_locator = (By.CSS_SELECTOR, 'div.no-data-overlay')

    @property
    def _page_title(self):
        return "%s :: Statistics Dashboard :: Add-ons for Firefox" % self.addon_name

    @property
    def is_chart_loaded(self):
        return self.is_element_present(*self._chart_locator) or self.is_element_visible(*self._no_data_locator)

    @property
    def addon_name(self):
        base = self.selenium.find_element(*self._title_locator).text
        return base.replace('Statistics for', '').strip()

    @property
    def total_downloads_number(self):
        text = self.selenium.find_element(*self._total_downloads_locator).text
        return int(text.split()[0].replace(',', ''))

########NEW FILE########
__FILENAME__ = themes
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
from unittestzero import Assert

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from pages.desktop.base import Base
from pages.desktop.search import SearchResultList


class Themes(Base):

    _page_title = "Themes :: Add-ons for Firefox"
    _themes_locator = (By.CSS_SELECTOR, 'div.persona.persona-small a')
    _start_exploring_locator = (By.CSS_SELECTOR, "#featured-addons.personas-home a.more-info")
    _featured_addons_locator = (By.CSS_SELECTOR, "#featured-addons.personas-home")

    _featured_themes_locator = (By.CSS_SELECTOR, ".personas-featured .persona.persona-small")
    _recently_added_locator = (By.CSS_SELECTOR, "#personas-created .persona-small")
    _most_popular_locator = (By.CSS_SELECTOR, "#personas-popular .persona-small")
    _top_rated_locator = (By.CSS_SELECTOR, "#personas-rating .persona-small")

    _theme_header_locator = (By.CSS_SELECTOR, ".featured-inner > h2")

    @property
    def theme_count(self):
        """Returns the total number of theme links in the page."""
        return len(self.selenium.find_elements(*self._themes_locator))

    def click_theme(self, index):
        """Clicks on the theme with the given index in the page."""
        WebDriverWait(self.selenium, self.timeout).until(lambda s: self.selenium.find_elements(*self._themes_locator)[index].is_displayed())
 
        self.selenium.find_elements(*self._themes_locator)[index].click()
        theme_detail = ThemesDetail(self.testsetup)

        WebDriverWait(self.selenium, self.timeout).until(lambda s: theme_detail.is_title_visible)
        return theme_detail

    def open_theme_detail_page(self, theme_key):
        self.selenium.get(self.base_url + "/addon/%s" % theme_key)
        return ThemesDetail(self.testsetup)

    def click_start_exploring(self):
        self.selenium.find_element(*self._start_exploring_locator).click()
        return ThemesBrowse(self.testsetup)

    @property
    def is_featured_addons_present(self):
        return len(self.selenium.find_elements(*self._featured_addons_locator)) > 0

    @property
    def featured_themes_count(self):
        return len(self.selenium.find_elements(*self._featured_themes_locator))

    @property
    def recently_added_count(self):
        return len(self.selenium.find_elements(*self._recently_added_locator))

    @property
    def recently_added_dates(self):
        iso_dates = self._extract_iso_dates("Added %B %d, %Y", *self._recently_added_locator)
        return iso_dates

    @property
    def most_popular_count(self):
        return len(self.selenium.find_elements(*self._most_popular_locator))

    @property
    def most_popular_downloads(self):
        pattern = "(\d+(?:[,]\d+)*)\s+users"
        return self._extract_integers(pattern, *self._most_popular_locator)

    @property
    def top_rated_count(self):
        return len(self.selenium.find_elements(*self._top_rated_locator))

    @property
    def top_rated_ratings(self):
        pattern = "Rated\s+(\d)\s+.*"
        return self._extract_integers(pattern, *self._top_rated_locator)

    @property
    def theme_header(self):
        return self.selenium.find_element(*self._theme_header_locator).text


class ThemesDetail(Base):

    _page_title_regex = '.+ :: Add-ons for Firefox'

    _themes_title_locator = (By.CSS_SELECTOR, 'h2.addon > span')
    _breadcrumb_locator = (By.ID, "breadcrumbs")

    @property
    def is_the_current_page(self):
        # This overrides the method in the Page super class.
        actual_page_title = self.page_title
        Assert.not_none(re.match(self._page_title_regex, actual_page_title), 'Expected the current page to be the themes detail page.\n Actual title: %s' % actual_page_title)
        return True

    @property
    def is_title_visible(self):
        return self.is_element_visible(*self._themes_title_locator)

    @property
    def title(self):
        return self.selenium.find_element(*self._themes_title_locator).text

    @property
    def breadcrumb(self):
        return self.selenium.find_element(*self._breadcrumb_locator).text


class ThemesBrowse(Base):

    _selected_sort_by_locator = (By.CSS_SELECTOR, '#addon-list-options li.selected a')
    _themes_grid_locator = (By.CSS_SELECTOR, '.featured.listing ul.personas-grid')

    @property
    def is_the_current_page(self):
        # This overrides the method in the Page super class.
        Assert.true(self.is_element_present(*self._themes_grid_locator),
                    'Expected the current page to be the themes browse page.')
        return True

    @property
    def sort_key(self):
        """Returns the current value of the sort request parameter."""
        url = self.selenium.current_url
        return re.search("[/][?]sort=(.+)[&]?", url).group(1)

    @property
    def sort_by(self):
        """Returns the label of the currently selected sort option."""
        return self.selenium.find_element(*self._selected_sort_by_locator).text


class ThemesSearchResultList(SearchResultList):
    _results_locator = (By.CSS_SELECTOR, 'ul.personas-grid div.persona-small')

    class ThemesSearchResultItem(SearchResultList.SearchResultItem):
        _name_locator = (By.CSS_SELECTOR, 'h6 > a')

########NEW FILE########
__FILENAME__ = user
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from pages.desktop.base import Base
from pages.page import Page


class Login(Base):

    _page_title = 'User Login :: Add-ons for Firefox'

    _email_locator = (By.ID, 'id_username')
    _password_locator = (By.ID, 'id_password')
    _login_button_locator = (By.ID, 'login-submit')
    _logout_locator = (By.CSS_SELECTOR, '.logout')
    _normal_login_locator = (By.ID, 'show-normal-login')
    _browser_id_locator = (By.CSS_SELECTOR, 'button.browserid-login')

    _pop_up_id = '_mozid_signin'

    def login_user_normal(self, user):
        credentials = self.testsetup.credentials[user]

        email = self.selenium.find_element(*self._email_locator)
        email.send_keys(credentials['email'])

        password = self.selenium.find_element(*self._password_locator)
        password.send_keys(credentials['password'])

        password.send_keys(Keys.RETURN)

    def login_user_browser_id(self, user):
        credentials = self.testsetup.credentials[user]
        from browserid import BrowserID
        pop_up = BrowserID(self.selenium, self.timeout)
        pop_up.sign_in(credentials['email'], credentials['password'])
        WebDriverWait(self.selenium, 20).until(lambda s: s.find_element(*self._logout_locator))


class ViewProfile(Base):

    _page_title = 'User Info for amo.testing :: Add-ons for Firefox'

    _about_locator = (By.CSS_SELECTOR, "div.island > section.primary > h2")
    _email_locator = (By.CSS_SELECTOR, 'a.email')

    def __init__(self, testsetup):
        Base.__init__(self, testsetup)
        WebDriverWait(self.selenium, self.timeout).until(
            lambda s: (s.find_element(*self._about_locator)).is_displayed())

    @property
    def about_me(self):
        return self.selenium.find_element(*self._about_locator).text

    @property
    def is_email_field_present(self):
        return self.is_element_present(*self._email_locator)

    @property
    def email_value(self):
        email = self.selenium.find_element(*self._email_locator).text
        return email[::-1]


class User(Base):

        _username_locator = (By.CSS_SELECTOR, ".fn.n")

        @property
        def username(self):
            return self.selenium.find_element(*self._username_locator).text


class EditProfile(Base):

    _page_title = 'Account Settings :: Add-ons for Firefox'

    _account_locator = (By.CSS_SELECTOR, "#acct-account > legend")
    _profile_locator = (By.CSS_SELECTOR, "#profile-personal > legend")
    _details_locator = (By.CSS_SELECTOR, "#profile-detail > legend")
    _notification_locator = (By.CSS_SELECTOR, "#acct-notify > legend")
    _hide_email_checkbox = (By.ID, 'id_emailhidden')
    _update_account_locator = (By.CSS_SELECTOR, 'p.footer-submit > button.prominent')
    _profile_fields_locator = (By.CSS_SELECTOR, '#profile-personal > ol.formfields li')
    _update_message_locator = (By.CSS_SELECTOR, 'div.notification-box > h2')

    def __init__(self, testsetup):
        Base.__init__(self, testsetup)
        WebDriverWait(self.selenium, self.timeout).until(
            lambda s: (s.find_element(*self._account_locator)).is_displayed())

    @property
    def account_header_text(self):
        return self.selenium.find_element(*self._account_locator).text

    @property
    def profile_header_text(self):
        return self.selenium.find_element(*self._profile_locator).text

    @property
    def details_header_text(self):
        return self.selenium.find_element(*self._details_locator).text

    @property
    def notification_header_text(self):
        return self.selenium.find_element(*self._notification_locator).text

    def click_update_account(self):
        self.selenium.find_element(*self._update_account_locator).click()
        WebDriverWait(self.selenium, self.timeout).until(lambda s: self.update_message == "Profile Updated")

    def change_hide_email_state(self):
        self.selenium.find_element(*self._hide_email_checkbox).click()

    @property
    def profile_fields(self):
        return [self.ProfileSection(self.testsetup, web_element)
                for web_element in self.selenium.find_elements(*self._profile_fields_locator)]

    @property
    def update_message(self):
        return self.selenium.find_element(*self._update_message_locator).text

    class ProfileSection(Page):

        _input_field_locator = (By.CSS_SELECTOR, ' input')
        _field_name = (By.CSS_SELECTOR, ' label')

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        @property
        def field_value(self):
            try:
                return self._root_element.find_element(*self._input_field_locator).get_attribute('value')
            except Exception.NoSuchAttributeException:
                return " "

        @property
        def field_name(self):
            return self._root_element.find_element(*self._field_name).text

        def type_value(self, value):
            if self.field_name == 'Homepage' and value != '':
                self._root_element.find_element(*self._input_field_locator).send_keys('http://example.com/' + value)
            else:
                self._root_element.find_element(*self._input_field_locator).send_keys(value)

        def clear_field(self):
            self._root_element.find_element(*self._input_field_locator).clear()


class MyCollections(Base):

    _header_locator = (By.CSS_SELECTOR, ".primary > header > h2")

    @property
    def my_collections_header_text(self):
        return self.selenium.find_element(*self._header_locator).text


class MyFavorites(Base):

    _header_locator = (By.CSS_SELECTOR, 'h2.collection > span')
    _page_title = 'My Favorite Add-ons :: Collections :: Add-ons for Firefox'

    @property
    def my_favorites_header_text(self):
        return self.selenium.find_element(*self._header_locator).text

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from pages.page import Page


class Base(Page):

    @property
    def scroll_down(self):
        """used as a workaround for selenium scroll issue"""
        self.selenium.execute_script('window.scrollTo(0,Math.max(document.documentElement.scrollHeight + document.body.scrollHeight,document.documentElement.clientHeight));')

    @property
    def footer(self):
        return Base.Footer(self.testsetup)

    @property
    def header(self):
        return Base.HeaderRegion(self.testsetup)

    class Footer(Page):
        _desktop_version_locator = (By.CSS_SELECTOR, 'a.desktop-link')
        _other_language_locator = (By.CSS_SELECTOR, '#language')
        _other_language_text_locator = (By.CSS_SELECTOR, '#lang_form > label')
        _privacy_locator = (By.CSS_SELECTOR, '#footer-links > a:nth-child(1)')
        _legal_locator = (By.CSS_SELECTOR, '#footer-links > a:nth-child(2)')

        def click_desktop_version(self):
            self.selenium.find_element(*self._desktop_version_locator).click()
            from pages.desktop.home import Home
            return Home(self.testsetup)

        @property
        def desktop_version_text(self):
            return self.selenium.find_element(*self._desktop_version_locator).text

        @property
        def other_language_text(self):
            return self.selenium.find_element(*self._other_language_text_locator).text

        @property
        def is_other_language_dropdown_visible(self):
            return self.is_element_visible(*self._other_language_locator)

        @property
        def privacy_text(self):
            return self.selenium.find_element(*self._privacy_locator).text

        @property
        def legal_text(self):
            return self.selenium.find_element(*self._legal_locator).text

    class HeaderRegion(Page):

        _dropdown_menu_locator = (By.CLASS_NAME, 'menu-items')
        _menu_items_locator = (By.CSS_SELECTOR, '.menu-items li')
        _menu_button_locator = (By.CSS_SELECTOR, '.tab > a')

        def click_header_menu(self):
            self.selenium.find_element(*self._menu_button_locator).click()

        @property
        def is_dropdown_menu_visible(self):
            return self.is_element_visible(*self._dropdown_menu_locator)

        @property
        def dropdown_menu_items(self):
            #returns a list containing all the menu items
            return [self.MenuItem(self.testsetup, web_element) for web_element in self.selenium.find_elements(*self._menu_items_locator)]

        class MenuItem(Page):

            _name_items_locator = (By.CSS_SELECTOR, 'a')

            def __init__(self, testsetup, element):
                Page.__init__(self, testsetup)
                self._root_element = element

            @property
            def name(self):
                return self._root_element.find_element(*self._name_items_locator).text

########NEW FILE########
__FILENAME__ = details
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re

from selenium.webdriver.common.by import By

from pages.mobile.base import Base


class Details(Base):

    _title_locator = (By.CSS_SELECTOR, 'div.infobox > h3')
    _contribute_button_locator = (By.XPATH, "//a[contains(.,'Contribute')]")

    def __init__(self, testsetup, addon_name=None):
        #formats name for url
        Base.__init__(self, testsetup)
        if (addon_name != None):
            self.addon_name = addon_name.replace(" ", "-")
            self.addon_name = re.sub(r'[^A-Za-z0-9\-]', '', self.addon_name).lower()
            self.addon_name = self.addon_name[:27]
            self.selenium.get("%s/addon/%s" % (self.base_url, self.addon_name))

    @property
    def _page_title(self):
        return "%s :: Add-ons for Firefox" % self.title

    @property
    def title(self):
        return self.selenium.find_element(*self._title_locator).text

    @property
    def is_contribute_button_present(self):
        return self.is_element_present(*self._contribute_button_locator)

########NEW FILE########
__FILENAME__ = extensions
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from pages.mobile.base import Base
from pages.page import Page


class Extensions(Base):

    _page_title_locator = (By.CSS_SELECTOR, 'h1.site-title > a')
    _page_header_locator = (By.CSS_SELECTOR, '#content > h2')
    _sort_by_locator = (By.CSS_SELECTOR, '.label > span')

    @property
    def page_header(self):
        return self.selenium.find_element(*self._page_header_locator).text

    @property
    def title(self):
        return str(self.selenium.find_element(*self._page_title_locator).text)

    def click_sort_by(self):
        self.selenium.find_element(*self._sort_by_locator).click()
        from pages.mobile.regions.sorter import Sorter
        return Sorter(self.testsetup)

########NEW FILE########
__FILENAME__ = home
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from pages.mobile.base import Base
from pages.page import Page


class Home(Base):

    _page_title = 'Add-ons for Firefox'

    _header_locator = (By.CSS_SELECTOR, 'h1.site-title > a')
    _header_logo_locator = (By.CSS_SELECTOR, '.site-title > a > img')
    _header_statement_locator = (By.CSS_SELECTOR, '#home-header > hgroup > h2')
    _learn_more_locator = (By.CSS_SELECTOR, '#learnmore')
    _learn_more_msg_locator = (By.CSS_SELECTOR, '#learnmore-msg')
    _tabs_locator = (By.CSS_SELECTOR, 'nav.tabs > ul > li')
    _search_box_locator = (By.CSS_SELECTOR, 'form#search > input')
    _search_button_locator = (By.CSS_SELECTOR, 'form#search > button')
    _logo_title_locator = (By.CSS_SELECTOR, 'h1.site-title > a')
    _logo_image_locator = (By.CSS_SELECTOR, 'h1.site-title > a > img')
    _subtitle_locator = (By.CSS_SELECTOR, 'hgroup > h2')

    _all_featured_addons_locator = (By.CSS_SELECTOR, '#list-featured > li > a')
    _default_selected_tab_locator = (By.CSS_SELECTOR, 'li.selected a')
    _categories_list_locator = (By.CSS_SELECTOR, '#listing-categories ul')
    _category_item_locator = (By.CSS_SELECTOR, 'li')

    def __init__(self, testsetup):
        Base.__init__(self, testsetup)
        self.selenium.get(self.base_url)
        self.is_the_current_page

    def search_for(self, search_term, click_button=True):
        search_box = self.selenium.find_element(*self._search_box_locator)
        search_box.send_keys(search_term)

        if click_button:
            self.selenium.find_element(*self._search_button_locator).click()
        else:
            search_box.submit()

        from pages.mobile.search_results import SearchResults
        return SearchResults(self.testsetup, search_term)

    @property
    def header_text(self):
        return self.selenium.find_element(*self._header_locator).text

    @property
    def header_title(self):
        return self.selenium.find_element(*self._header_locator).get_attribute('title')

    @property
    def header_statement_text(self):
        return self.selenium.find_element(*self._header_statement_locator).text

    @property
    def is_header_firefox_logo_visible(self):
        return self.selenium.find_element(*self._header_logo_locator).is_displayed()

    @property
    def firefox_header_logo_src(self):
        return self.selenium.find_element(*self._header_logo_locator).get_attribute('src')

    @property
    def learn_more_text(self):
        return self.selenium.find_element(*self._learn_more_locator).text

    def click_learn_more(self):
        self.selenium.find_element(*self._learn_more_locator).click()

    @property
    def learn_more_msg_text(self):
        return self.selenium.find_element(*self._learn_more_msg_locator).text

    @property
    def is_learn_more_msg_visible(self):
        return self.is_element_visible(*self._learn_more_msg_locator)

    def click_all_featured_addons_link(self):
        self.selenium.find_element(*self._all_featured_addons_locator).click()
        from pages.mobile.extensions import Extensions
        extensions_page = Extensions(self.testsetup)
        WebDriverWait(self.selenium, self.timeout).until(lambda s: self.is_element_visible(*extensions_page._sort_by_locator))
        return extensions_page

    @property
    def default_selected_tab_text(self):
        return self.selenium.find_element(*self._default_selected_tab_locator).text

    @property
    def tabs(self):
        return [self.Tabs(self.testsetup, web_element)
                for web_element in self.selenium.find_elements(*self._tabs_locator)]

    def tab(self, value):
        if type(value) == int:
            return self.tabs[value]
        elif type(value) == str:
            for tab in self.tabs:
                if tab.name == value:
                    return tab

    class Tabs(Page):

        _tab_name_locator = (By.CSS_SELECTOR, 'a')
        _tab_content_locator = (By.ID, 'listing')

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        @property
        def name(self):
            return self._root_element.find_element(*self._tab_name_locator).text

        def click(self):
            self._root_element.find_element(*self._tab_name_locator).click()

        @property
        def is_tab_selected(self):
            is_selected = self._root_element.get_attribute('class')
            return 'selected' in is_selected

        @property
        def is_tab_content_visible(self):
            content = (self._tab_content_locator[0], '%s-%s' % (self._tab_content_locator[1], self.name.lower()))
            return self.is_element_visible(*content)

    @property
    def is_search_box_visible(self):
        return self.is_element_visible(*self._search_box_locator)

    @property
    def search_box_placeholder(self):
        return self.selenium.find_element(*self._search_box_locator).get_attribute('placeholder')

    @property
    def is_search_button_visible(self):
        return self.is_element_visible(*self._search_button_locator)

    @property
    def logo_title(self):
        return self.selenium.find_element(*self._logo_title_locator).get_attribute('title')

    @property
    def logo_text(self):
        return self.selenium.find_element(*self._logo_title_locator).text

    @property
    def logo_image_src(self):
        return self.selenium.find_element(*self._logo_image_locator).get_attribute('src')

    @property
    def subtitle(self):
        return self.selenium.find_element(*self._subtitle_locator).text

    @property
    def is_categories_region_visible(self):
        return self.is_element_visible(*self._categories_list_locator)

    @property
    def categories(self):
        return [self.Category(self.testsetup, category_element)
                for category_element in self.selenium.find_element(*self._categories_list_locator).find_elements(*self._category_item_locator)]

    class Category(Page):

        _link_locator = (By.TAG_NAME, 'a')

        def __init__(self, testsetup, category_element):
            Page.__init__(self, testsetup)
            self._root_element = category_element

        @property
        def name(self):
            return self._root_element.text

########NEW FILE########
__FILENAME__ = addon_list_item
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pages.page import Page


class AddonItem(Page):

    def __init__(self, testsetup, element):
        Page.__init__(self, testsetup)
        self._root_element = element

########NEW FILE########
__FILENAME__ = sorter
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By
from pages.mobile.base import Base
from pages.page import Page


class Sorter(Page):

    _menu_locator = (By.CSS_SELECTOR, '#sort-menu ul')
    _menu_option_locator = (By.CSS_SELECTOR, 'li')

    @property
    def is_extensions_dropdown_visible(self):
        return self.is_element_visible(*self._menu_locator)

    @property
    def options(self):
        return [self.SortOption(self.testsetup, element)
                for element in self.selenium.find_element(*self._menu_locator).find_elements(*self._menu_option_locator)]

    class SortOption(Page):

        _name_locator = (By.CSS_SELECTOR, 'a')

        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        @property
        def name(self):
            return self._root_element.find_element(*self._name_locator).text

        @property
        def is_option_visible(self):
            return self._root_element.find_element(*self._name_locator).is_displayed()

########NEW FILE########
__FILENAME__ = search_results
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from selenium.webdriver.common.by import By

from pages.mobile.base import Base


class SearchResults(Base):

    _results_locator = (By.CSS_SELECTOR, '.addon-listing .item')

    def __init__(self, testsetup, search_term):
        Base.__init__(self, testsetup)
        self._page_title = "%s :: Search :: Add-ons for Firefox" % search_term

    @property
    def results(self):
        from pages.mobile.regions.addon_list_item import AddonItem
        return [AddonItem(self.testsetup, element)
                for element in self.selenium.find_elements(*self._results_locator)]

########NEW FILE########
__FILENAME__ = themes
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pages.mobile.base import Base


class Themes(Base):

    _page_title = 'Themes :: Add-ons for Firefox'

########NEW FILE########
__FILENAME__ = page
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
Created on Jun 21, 2010

'''
from unittestzero import Assert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotVisibleException


class Page(object):
    """
    Base class for all Pages.
    """

    def __init__(self, testsetup):
        """
        Constructor
        """
        self.testsetup = testsetup
        self.base_url = testsetup.base_url
        self.api_base_url = testsetup.api_base_url
        self.selenium = testsetup.selenium
        self.timeout = testsetup.timeout

    def get_url(self, url):
        self.selenium.get(url)

    @property
    def is_the_current_page(self):
        WebDriverWait(self.selenium, self.timeout).until(
            lambda s: s.title == self._page_title,
            "Expected page title: %s. Actual page title: %s" % (self._page_title, self.selenium.title))
        return True

    def get_url_current_page(self):
        WebDriverWait(self.selenium, self.timeout).until(lambda s: self.selenium.title)
        return self.selenium.current_url

    def is_element_present(self, *locator):
        self.selenium.implicitly_wait(0)
        try:
            self.selenium.find_element(*locator)
            return True
        except NoSuchElementException:
            return False
        finally:
            # set back to where you once belonged
            self.selenium.implicitly_wait(self.testsetup.default_implicit_wait)

    def is_element_visible(self, *locator):
        try:
            return self.selenium.find_element(*locator).is_displayed()
        except (NoSuchElementException, ElementNotVisibleException):
            return False

    def return_to_previous_page(self):
        self.selenium.back()

########NEW FILE########
__FILENAME__ = test_api_only
#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from unittestzero import Assert

from pages.desktop.addons_api import AddonsAPI

#These tests should only call the api.
#There should be no tests requiring selenium in this class.


@pytest.mark.skip_selenium
class TestAPIOnlyTests:

    @pytest.mark.nondestructive
    def test_that_firebug_is_listed_first_in_addons_search_for_firebug(self, mozwebqa):
        response = AddonsAPI(mozwebqa, 'Firebug')
        Assert.equal("Firebug".lower(), response.get_addon_name())

    @pytest.mark.nondestructive
    def test_that_firebug_addon_type_name_is_extension(self, mozwebqa):
        response = AddonsAPI(mozwebqa, 'Firebug')
        Assert.equal("Extension".lower(), response.get_addon_type())

    @pytest.mark.nondestructive
    def test_that_firebug_addon_type_id_is_1(self, mozwebqa):
        response = AddonsAPI(mozwebqa, 'Firebug')
        Assert.equal(1, response.get_addon_type_id())

    @pytest.mark.nondestructive
    def test_that_firebug_status_id_is_4_and_fully_reviewed(self, mozwebqa):
        response = AddonsAPI(mozwebqa, 'Firebug')
        Assert.equal(4, response.get_addon_status_id())
        Assert.equal("fully reviewed".lower(), response.get_addon_status())

    @pytest.mark.nondestructive
    def test_that_firebug_has_install_link(self, mozwebqa):
        response = AddonsAPI(mozwebqa, 'Firebug')
        Assert.contains("fx.xpi?src=api", response.get_install_link())

########NEW FILE########
__FILENAME__ = test_collections
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
import time
import uuid

from unittestzero import Assert

from pages.desktop.home import Home
from pages.desktop.details import Details


class TestCollections:

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_featured_tab_is_highlighted_by_default(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_collections_page = home_page.header.site_navigation_menu("Collections").click()
        Assert.equal(featured_collections_page.default_selected_tab, "Featured")

    @pytest.mark.login
    def test_create_and_delete_collection(self, mozwebqa):

        home_page = Home(mozwebqa)
        collections_page = home_page.header.site_navigation_menu('Collections').click()
        create_collection_page = collections_page.click_create_collection_button()
        home_page.login()

        collection_uuid = uuid.uuid4().hex
        collection_time = repr(time.time())
        collection_name = collection_uuid[:30 - len(collection_time):] + collection_time

        create_collection_page.type_name(collection_name)
        create_collection_page.type_description(collection_name)
        collection = create_collection_page.click_create_collection()

        Assert.equal(collection.notification, 'Collection created!')
        Assert.equal(collection.collection_name, collection_name)
        collection.delete()
        user_collections = collection.delete_confirmation()
        if user_collections.has_no_results:
            pass
        else:
            for collection_element in range(len(user_collections.collections)):  # If the condition is satisfied, iterate through the collections items on the page
                Assert.true(collection_name not in user_collections.collections[collection_element].text)  # Check for each collection that the name is not the same as the deleted collections name

    @pytest.mark.native
    @pytest.mark.nondestructive
    @pytest.mark.login
    def test_user_my_collections_page(self, mozwebqa):

        home_page = Home(mozwebqa)
        home_page.login()
        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.header.is_user_logged_in)

        username = mozwebqa.credentials['default']['name']
        my_collections_page = home_page.header.click_my_collections()
        Assert.equal('Collections by %s :: Add-ons for Firefox' % username, home_page.page_title)
        Assert.equal('Collections by %s' % username, my_collections_page.my_collections_header_text)

    @pytest.mark.native
    @pytest.mark.login
    def test_user_my_favorites_page(self, mozwebqa):

        home_page = Home(mozwebqa)
        home_page.login()
        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.header.is_user_logged_in)

        # mark an add-on as favorite if there is none
        if not home_page.header.is_my_favorites_menu_present:
            details_page = Details(mozwebqa, 'Firebug')
            # sometimes the call to is_my_favorites_menu_present lies
            # and clicking the add to favorites locator when it's already favorited
            # makes things worse
            if not details_page.is_addon_marked_as_favorite:
                details_page.click_add_to_favorites()
                Assert.true(details_page.is_addon_marked_as_favorite)
            home_page = Home(mozwebqa)

        my_favorites_page = home_page.header.click_my_favorites()
        Assert.true(my_favorites_page.is_the_current_page)
        Assert.equal('My Favorite Add-ons', my_favorites_page.my_favorites_header_text)

########NEW FILE########
__FILENAME__ = test_complete_themes
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from unittestzero import Assert

from pages.desktop.home import Home


class TestCompleteThemes:

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_complete_themes_can_be_sorted_by_name(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        complete_themes_page.click_sort_by("name")
        addons = complete_themes_page.addon_names
        addons_set = set(addons)
        Assert.equal(len(addons), len(addons_set), "There are duplicates in the names")
        addons_orig = addons
        addons.sort()
        [Assert.equal(addons_orig[i], addons[i]) for i in xrange(len(addons))]
        complete_themes_page.paginator.click_next_page()
        addons = complete_themes_page.addon_names
        addons_set = set(addons)
        Assert.equal(len(addons), len(addons_set), "There are duplicates in the names")
        addons_orig = addons
        addons.sort()
        [Assert.equal(addons_orig[i], addons[i]) for i in xrange(len(addons))]

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_complete_themes_can_be_sorted_by_updated_date(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        complete_themes_page.click_sort_by("recently updated")
        addons = complete_themes_page.addon_names
        addons_set = set(addons)
        Assert.equal(len(addons), len(addons_set), "There are duplicates in the names")
        updated_dates = complete_themes_page.addon_updated_dates
        Assert.is_sorted_descending(updated_dates)
        complete_themes_page.paginator.click_next_page()
        updated_dates.extend(complete_themes_page.addon_updated_dates)
        Assert.is_sorted_descending(updated_dates)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_complete_themes_can_be_sorted_by_created_date(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        complete_themes_page.click_sort_by("newest")
        addons = complete_themes_page.addon_names
        addons_set = set(addons)
        Assert.equal(len(addons), len(addons_set), "There are duplicates in the names")
        created_dates = complete_themes_page.addon_created_dates
        Assert.is_sorted_descending(created_dates)
        complete_themes_page.paginator.click_next_page()
        created_dates.extend(complete_themes_page.addon_created_dates)
        Assert.is_sorted_descending(created_dates)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_complete_themes_can_be_sorted_by_popularity(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        complete_themes_page.click_sort_by("weekly downloads")
        addons = complete_themes_page.addon_names
        addons_set = set(addons)
        Assert.equal(len(addons), len(addons_set), "There are duplicates in the names")
        downloads = complete_themes_page.addon_download_number
        Assert.is_sorted_descending(downloads)
        complete_themes_page.paginator.click_next_page()
        downloads.extend(complete_themes_page.addon_download_number)
        Assert.is_sorted_descending(downloads)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_complete_themes_loads_landing_page_correctly(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        url_current_page = complete_themes_page.get_url_current_page()
        Assert.true(url_current_page.endswith("/complete-themes/"))

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_clicking_on_complete_theme_name_loads_its_detail_page(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        complete_theme_name = complete_themes_page.addon_name(1)
        complete_theme_page = complete_themes_page.click_on_first_addon()
        Assert.contains(complete_theme_name, complete_theme_page.addon_title)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_complete_themes_page_has_correct_title(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        expected_title = "Most Popular Complete Themes :: Add-ons for Firefox"
        Assert.equal(expected_title, complete_themes_page.page_title)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_complete_themes_page_breadcrumb(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        expected_breadcrumb = "Complete Themes"
        Assert.equal(expected_breadcrumb, complete_themes_page.breadcrumbs[1].text)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_clicking_on_a_subcategory_loads_expected_page(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        selected_category = complete_themes_page.complete_themes_category
        amo_category_page = complete_themes_page.click_on_first_category()
        Assert.equal(selected_category, amo_category_page.title)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_complete_themes_subcategory_page_breadcrumb(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        selected_category = complete_themes_page.complete_themes_category
        amo_category_page = complete_themes_page.click_on_first_category()
        expected_breadcrumbs = ['Add-ons for Firefox', 'Complete Themes', selected_category]

        [Assert.equal(expected_breadcrumbs[i], amo_category_page.breadcrumbs[i].text) for i in range(len(amo_category_page.breadcrumbs))]

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_complete_themes_categories_are_listed_on_left_hand_side(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        current_page_url = home_page.get_url_current_page()
        Assert.true(current_page_url.endswith("/complete-themes/"))
        default_categories = ["Animals", "Compact", "Large", "Miscellaneous", "Modern", "Nature", "OS Integration", "Retro", "Sports"]
        Assert.equal(complete_themes_page.categories_count, len(default_categories))
        count = 0
        for category in default_categories:
            count += 1
            current_category = complete_themes_page.get_category(count)
            Assert.equal(category, current_category)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_complete_themes_categories_are_not_extensions_categories(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        complete_themes_categories = complete_themes_page.get_all_categories

        home_page.header.site_navigation_menu("Extensions").click()
        extensions_categories = complete_themes_page.get_all_categories

        Assert.not_equal(len(complete_themes_categories), len(extensions_categories))
        Assert.equal(list(set(complete_themes_categories) & set(extensions_categories)), [])

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_last_complete_themes_page_is_not_empty(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        complete_themes_page.paginator.click_last_page()
        Assert.greater_equal(complete_themes_page.addon_count, 1)

    @pytest.mark.xfail("'mac' in config.getvalue('platform')",
                       reason="https://github.com/mozilla/Addon-Tests/issues/705")
    @pytest.mark.action_chains
    @pytest.mark.nondestructive
    def test_the_displayed_message_for_incompatible_complete_themes(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()

        complete_themes = complete_themes_page.complete_themes

        for complete_theme in complete_themes:
            if complete_theme.is_incompatible:
                Assert.true(complete_theme.is_incompatible_flag_visible)
                Assert.contains('Not available',
                             complete_theme.not_available_flag_text)
            else:
                Assert.false(complete_theme.is_incompatible_flag_visible)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_most_popular_link_is_default(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        url_current_page = complete_themes_page.get_url_current_page()
        Assert.true(url_current_page.endswith("/complete-themes/"))
        Assert.equal(complete_themes_page.selected_explore_filter, 'Most Popular')

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_sorted_by_most_users_is_default(self, mozwebqa):
        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        url_current_page = complete_themes_page.get_url_current_page()
        Assert.true(url_current_page.endswith("/complete-themes/"))
        Assert.equal(complete_themes_page.sorted_by, 'Most Users')

########NEW FILE########
__FILENAME__ = test_details_page
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import re
import pytest

from unittestzero import Assert

from pages.desktop.details import Details
from pages.desktop.extensions import ExtensionsHome
from pages.desktop.home import Home


class TestDetails:

    @pytest.mark.login
    @pytest.mark.nondestructive
    def test_that_register_login_link_is_present_in_addon_details_page(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        if details_page.header.is_browserid_login_available:
            Assert.true(details_page.header.is_browserid_login_available)
        else:
            Assert.true(details_page.header.is_register_link_visible, "Register link is not visible")
            Assert.true(details_page.header.is_login_link_visible, "Login links is not visible")

    @pytest.mark.action_chains
    @pytest.mark.nondestructive
    def test_that_dropdown_menu_is_present_after_click_on_other_apps(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        Assert.equal(details_page.header.menu_name, "Other Applications")
        details_page.header.hover_over_other_apps_menu()
        Assert.true(details_page.header.is_other_apps_dropdown_menu_visible)

    @pytest.mark.nondestructive
    def test_that_addon_name_is_displayed(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        # check that the name is not empty
        Assert.not_none(details_page.title, "")

    @pytest.mark.nondestructive
    def test_that_summary_is_displayed(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        # check that the summary is not empty
        Assert.not_none(re.match('(\w+\s*){3,}', details_page.summary))

    @pytest.mark.nondestructive
    def test_that_about_this_addon_is_displayed(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        Assert.equal(details_page.about_addon, "About this Add-on")
        Assert.not_none(re.match('(\w+\s*){3,}', details_page.description))

    @pytest.mark.action_chains
    @pytest.mark.nondestructive
    def test_that_version_information_is_displayed(self, mozwebqa):
        details_page = Details(mozwebqa, 'Firebug')
        Assert.equal(details_page.version_information_heading, 'Version Information')

        details_page.expand_version_information()
        Assert.true(details_page.is_version_information_section_expanded)
        Assert.true(details_page.is_source_code_license_information_visible)
        Assert.true(details_page.is_whats_this_license_visible)
        Assert.true(details_page.is_view_the_source_link_visible)
        Assert.true(details_page.is_complete_version_history_visible)
        Assert.true(details_page.is_version_information_install_button_visible)
        # check that the release number matches the version number at the top of the page
        Assert.equal('Version %s' % details_page.version_number, details_page.release_version)

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_that_reviews_are_displayed(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        Assert.equal(details_page.review_title, "Reviews")
        Assert.true(details_page.has_reviews)
        for review in details_page.review_details:
            Assert.not_none(review)

    @pytest.mark.nondestructive
    def test_that_in_often_used_with_addons_are_displayed(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        Assert.equal(details_page.often_used_with_header, u"Often used with\u2026")
        Assert.true(details_page.is_often_used_with_list_visible)

    @pytest.mark.nondestructive
    def test_that_tags_are_displayed(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        Assert.true(details_page.are_tags_visible)

    @pytest.mark.nondestructive
    def test_part_of_collections_are_displayed(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        Assert.equal(details_page.part_of_collections_header, 'Part of these Collections')
        Assert.true(len(details_page.part_of_collections) > 0)

    @pytest.mark.nondestructive
    def test_that_external_link_leads_to_addon_website(self, mozwebqa):

        # Step 1 - Open AMO Home
        # Step 2 - Open MemChaser Plus details page
        details_page = Details(mozwebqa, 'MemChaser')
        website_link = details_page.website
        Assert.true(website_link != '')
        # Step 3 - Follow external website link
        details_page.click_website_link()
        Assert.contains(details_page.get_url_current_page(), website_link)

    @pytest.mark.nondestructive
    def test_that_whats_this_link_for_source_license_links_to_an_answer_in_faq(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        details_page.expand_version_information()
        user_faq_page = details_page.click_whats_this_license()
        Assert.not_none(re.match('(\w+\s*){3,}', user_faq_page.license_question))
        Assert.not_none(re.match('(\w+\s*){3,}', user_faq_page.license_answer))

    @pytest.mark.nondestructive
    def test_other_addons_label_when_there_are_multiple_authors(self, mozwebqa):
        addon_with_multiple_authors = 'firebug'
        detail_page = Details(mozwebqa, addon_with_multiple_authors)

        Assert.true(len(detail_page.authors) > 1)
        Assert.equal(detail_page.other_addons_by_authors_text, 'Other add-ons by these authors')

    @pytest.mark.nondestructive
    def test_other_addons_label_when_there_is_only_one_author(self, mozwebqa):
        addon_with_one_authors = 'F1 by Mozilla Labs'
        detail_page = Details(mozwebqa, addon_with_one_authors)

        Assert.equal(len(detail_page.authors), 1)
        Assert.equal(detail_page.other_addons_by_authors_text, "Other add-ons by %s" % detail_page.authors[0])

    @pytest.mark.nondestructive
    def test_navigating_to_other_addons(self, mozwebqa):
        detail_page = Details(mozwebqa, 'firebug')

        for i in range(0, len(detail_page.other_addons)):
            name = detail_page.other_addons[i].name
            detail_page.other_addons[i].click_addon_link()
            Assert.contains(name, detail_page.title)
            Details(mozwebqa, 'firebug')

    @pytest.mark.nondestructive
    def test_open_close_functionality_for_image_viewer(self, mozwebqa):

        detail_page = Details(mozwebqa, 'firebug')

        image_viewer = detail_page.previewer.click_image()
        Assert.true(image_viewer.is_visible)
        image_viewer.close()
        Assert.false(image_viewer.is_visible)

    @pytest.mark.nondestructive
    def test_navigation_buttons_for_image_viewer(self, mozwebqa):

        detail_page = Details(mozwebqa, 'firebug')
        images_count = detail_page.previewer.image_count
        image_set_count = detail_page.previewer.image_set_count
        images_title = []
        image_link = []
        for img_set in range(image_set_count):
            for img_no in range(3):
                if img_set * 3 + img_no != images_count:
                    images_title.append(detail_page.previewer.image_title(img_set * 3 + img_no))
                    image_link.append(detail_page.previewer.image_link(img_set * 3 + img_no))

            detail_page.previewer.next_set()

        for img_set in range(image_set_count):
            detail_page.previewer.prev_set()

        image_viewer = detail_page.previewer.click_image()
        Assert.true(image_viewer.is_visible)
        Assert.equal(images_count, image_viewer.images_count)

        for i in range(image_viewer.images_count):
            Assert.true(image_viewer.is_visible)

            Assert.equal(image_viewer.caption, images_title[i])
            Assert.equal(image_viewer.image_link.split('/')[8], image_link[i].split('/')[8])

            if not i == 0:
                Assert.true(image_viewer.is_previous_present)
            else:
                Assert.false(image_viewer.is_previous_present)

            if not i == image_viewer.images_count - 1:
                Assert.true(image_viewer.is_next_present)
                image_viewer.click_next()
            else:
                Assert.false(image_viewer.is_next_present)

        for i in range(image_viewer.images_count - 1, -1, -1):
            Assert.true(image_viewer.is_visible)

            Assert.equal(image_viewer.caption, images_title[i])
            Assert.equal(image_viewer.image_link.split('/')[8], image_link[i].split('/')[8])

            if not i == image_viewer.images_count - 1:
                Assert.true(image_viewer.is_next_present)
            else:
                Assert.false(image_viewer.is_next_present)

            if not i == 0:
                Assert.true(image_viewer.is_previous_present)
                image_viewer.click_previous()
            else:
                Assert.false(image_viewer.is_previous_present)

    @pytest.mark.nondestructive
    def test_that_review_usernames_are_clickable(self, mozwebqa):
        addon_name = 'firebug'
        detail_page = Details(mozwebqa, addon_name)

        for i in range(0, len(detail_page.reviews)):
            username = detail_page.reviews[i].username
            amo_user_page = detail_page.reviews[i].click_username()
            Assert.equal(username, amo_user_page.username)
            Details(mozwebqa, addon_name)

    @pytest.mark.nondestructive
    def test_that_details_page_has_breadcrumb(self, mozwebqa):
        detail_page = Details(mozwebqa, 'firebug')
        Assert.equal(detail_page.breadcrumbs[0].text, 'Add-ons for Firefox')
        Assert.equal(detail_page.breadcrumbs[1].text, 'Extensions')
        Assert.equal(detail_page.breadcrumbs[2].text, 'Firebug')

    @pytest.mark.nondestructive
    def test_that_clicking_info_link_slides_down_page_to_version_info(self, mozwebqa):
        details_page = Details(mozwebqa, 'firebug')
        details_page.click_version_info_link()
        Assert.equal(details_page.version_info_link, details_page.version_information_href)
        Assert.true(details_page.is_version_information_section_expanded)
        Assert.true(details_page.is_version_information_section_in_view)

    @pytest.mark.nondestructive
    def test_that_breadcrumb_links_in_details_page_work(self, mozwebqa):
        home_page = Home(mozwebqa)
        detail_page = Details(mozwebqa, 'firebug')

        Assert.equal(detail_page.breadcrumbs[0].text, 'Add-ons for Firefox')
        link = detail_page.breadcrumbs[0].href_value
        detail_page.breadcrumbs[0].click()

        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.get_url_current_page().endswith(link))

        home_page.return_to_previous_page()

        Assert.equal(detail_page.breadcrumbs[1].text, 'Extensions')
        link = detail_page.breadcrumbs[1].href_value
        detail_page.breadcrumbs[1].click()

        amo_extenstions_page = ExtensionsHome(mozwebqa)
        Assert.true(amo_extenstions_page.is_the_current_page)
        Assert.true(amo_extenstions_page.get_url_current_page().endswith(link))

        home_page.return_to_previous_page()

        Assert.equal(detail_page.breadcrumbs[2].text, 'Firebug')

    @pytest.mark.nondestructive
    @pytest.mark.login
    def test_that_add_a_review_button_works(self, mozwebqa):
        #Step 1: Addons Home Page loads and Addons Details loads
        home_page = Home(mozwebqa)

        #Step 2:user logs in to submit a review
        home_page.login()
        Assert.true(home_page.header.is_user_logged_in)

        #Step 3: user loads an addon details page and clicks write a review button
        details_page = Details(mozwebqa, 'Firebug')
        review_box = details_page.click_to_write_review()
        Assert.true(review_box.is_review_box_visible)

    @pytest.mark.nondestructive
    def test_the_developers_comments_section(self, mozwebqa):
        details_page = Details(mozwebqa, 'Firebug')
        Assert.equal(details_page.devs_comments_title, u"Developer\u2019s Comments")
        details_page.expand_devs_comments()
        Assert.true(details_page.is_devs_comments_section_expanded)
        Assert.not_none(re.match('(\w+\s*){3,}', details_page.devs_comments_message))

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_that_add_to_collection_flyout_for_anonymous_users(self, mozwebqa):
        details_page = Details(mozwebqa, 'Firebug')
        details_page.click_add_to_collection_widget()
        Assert.equal(details_page.collection_widget_button, 'Create an Add-ons Account')
        Assert.equal(details_page.collection_widget_login_link, 'log in to your current account')

    @pytest.mark.nondestructive
    def test_that_the_development_channel_expands(self, mozwebqa):
        details_page = Details(mozwebqa, 'Firebug')
        Assert.equal("Development Channel", details_page.development_channel_text)

        Assert.equal('', details_page.development_channel_content)
        details_page.click_development_channel()
        Assert.not_none(details_page.development_channel_content)
        details_page.click_development_channel()
        Assert.equal('', details_page.development_channel_content)

    @pytest.mark.nondestructive
    def test_click_on_other_collections(self, mozwebqa):
        details_pg = Details(mozwebqa, 'Firebug')

        for i in range(0, len(details_pg.part_of_collections)):
            name = details_pg.part_of_collections[i].name
            collection_pg = details_pg.part_of_collections[i].click_collection()
            Assert.equal(name, collection_pg.collection_name, "Expected collection name does not match the page header")
            details_pg = Details(mozwebqa, 'Firebug')

    @pytest.mark.nondestructive
    def test_the_development_channel_section(self, mozwebqa):
        details_page = Details(mozwebqa, 'Firebug')

        Assert.equal('Development Channel', details_page.development_channel_text)
        details_page.click_development_channel()

        # Verify if description present
        Assert.not_none(details_page.development_channel_content)
        Assert.true(details_page.is_development_channel_install_button_visible)

        # Verify experimental version (beta or pre)
        Assert.not_none(re.match('Version\s\d+\.\d+\.\d+[a|b|rc]\d+\:', details_page.beta_version))

    @pytest.mark.nondestructive
    def test_that_license_link_works(self, mozwebqa):
        addon_name = 'Firebug'
        details_page = Details(mozwebqa, addon_name)
        Assert.equal(details_page.license_link_text, 'BSD License')
        license_link = details_page.license_site
        Assert.not_none(license_link)

    @pytest.mark.nondestructive
    def test_that_clicking_user_reviews_slides_down_page_to_reviews_section(self, mozwebqa):
        details_page = Details(mozwebqa, 'firebug')
        details_page.click_user_reviews_link()

        Assert.true(details_page.is_reviews_section_visible)
        Assert.true(details_page.is_reviews_section_in_view)

    @pytest.mark.action_chains
    @pytest.mark.nondestructive
    def test_that_install_button_is_clickable(self, mozwebqa):
        """
        https://www.pivotaltracker.com/story/show/27212263
        """
        details_page = Details(mozwebqa, 'firebug')
        Assert.contains("active", details_page.click_and_hold_install_button_returns_class_value())

    @pytest.mark.nondestructive
    def test_what_is_this_in_the_version_information(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        Assert.equal(details_page.version_information_heading, "Version Information")
        details_page.expand_version_information()
        Assert.equal("What's this?", details_page.license_faq_text)
        license_faq = details_page.click_whats_this_license()
        Assert.equal("Frequently Asked Questions", license_faq.header_text)

    @pytest.mark.nondestructive
    def test_view_the_source_in_the_version_information(self, mozwebqa):
        details_page = Details(mozwebqa, "Firebug")
        Assert.equal(details_page.version_information_heading, "Version Information")
        details_page.expand_version_information()
        Assert.equal("View the source", details_page.view_source_code_text)
        view_source = details_page.click_view_source_code()
        Assert.contains('/files/browse/', view_source.get_url_current_page())

########NEW FILE########
__FILENAME__ = test_details_page_against_xml
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
from urllib2 import urlparse

import pytest
from unittestzero import Assert

from pages.desktop.details import Details
from pages.desktop.addons_api import AddonsAPI


class TestDetailsAgainstXML:

    firebug = "Firebug"

    @pytest.mark.nondestructive
    def test_that_firebug_page_title_is_correct(self, mozwebqa):
        firebug_page = Details(mozwebqa, self.firebug)
        Assert.true(re.search(self.firebug, firebug_page.page_title) is not None)

    @pytest.mark.nondestructive
    def test_that_firebug_version_number_is_correct(self, mozwebqa):
        firebug_page = Details(mozwebqa, self.firebug)
        Assert.true(len(str(firebug_page.version_number)) > 0)

    @pytest.mark.nondestructive
    def test_that_firebug_authors_is_correct(self, mozwebqa):

        #get authors from browser
        firebug_page = Details(mozwebqa, self.firebug)
        browser_authors = firebug_page.authors

        #get authors from xml
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_authors = addons_xml.get_list_of_addon_author_names()

        #check that both lists have the same number of authors
        Assert.equal(len(browser_authors), len(xml_authors))

        #cross check both lists with each other
        for i in range(len(xml_authors)):
            Assert.equal(xml_authors[i], browser_authors[i])

    @pytest.mark.nondestructive
    def test_that_firebug_images_is_correct(self, mozwebqa):

        #get images links from browser
        firebug_page = Details(mozwebqa, self.firebug)
        images_count = firebug_page.previewer.image_count
        browser_images = []
        for i in range(images_count):
            browser_images.append(firebug_page.previewer.image_link(i))

        #get images links from xml
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_images = addons_xml.get_list_of_addon_images_links()

        #check that both lists have the same number of images
        Assert.equal(len(browser_images), len(xml_images))

        #cross check both lists with each other
        for i in range(len(xml_images)):
            Assert.equal(
                re.sub('src=api(&amp;|&)', '', xml_images[i]),
                browser_images[i])

    @pytest.mark.nondestructive
    def test_that_firebug_summary_is_correct(self, mozwebqa):

        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        browser_summary = firebug_page.summary

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_summary = addons_xml.get_addon_summary()

        Assert.equal(xml_summary, browser_summary)

    @pytest.mark.nondestructive
    def test_that_firebug_rating_is_correct(self, mozwebqa):
        firebug_page = Details(mozwebqa, self.firebug)
        Assert.equal("5", firebug_page.rating)

    @pytest.mark.nondestructive
    def test_that_description_text_is_correct(self, mozwebqa):
        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        browser_description = firebug_page.description

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_description = addons_xml.get_addon_description()

        Assert.equal(
            browser_description.replace('\n', ''),
            xml_description.replace('\n', ''))

    @pytest.mark.nondestructive
    def test_that_icon_is_correct(self, mozwebqa):

        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        browser_icon = firebug_page.icon_url

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)

        xml_icon = addons_xml.get_icon_url()

        Assert.equal(browser_icon, xml_icon)

    @pytest.mark.nondestructive
    def test_that_support_url_is_correct(self, mozwebqa):

        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        browser_support_url = firebug_page.support_url

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_support_url = addons_xml.get_support_url()

        Assert.equal(browser_support_url, xml_support_url)

    @pytest.mark.nondestructive
    def test_that_rating_in_api_equals_rating_in_details_page(self, mozwebqa):

        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        browser_rating = firebug_page.rating

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_rating = addons_xml.get_rating()

        Assert.equal(browser_rating, xml_rating)

    @pytest.mark.nondestructive
    def test_that_compatible_applications_equal(self, mozwebqa):

        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        firebug_page.expand_version_information()
        browser_compatible_applications = firebug_page.compatible_applications

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_compatible_applications = addons_xml.get_compatible_applications()
        name = xml_compatible_applications[0]
        min_version = xml_compatible_applications[1]
        max_version = xml_compatible_applications[2]
        
        # E.g.: Works with Firefox 1.0
        meta_compat_prefix = 'Works with %s %s ' % (name, min_version)
        # E.g.: Works with Firefox 1.0 and later
        meta_compat_abbrev = meta_compat_prefix + 'and later'
        # E.g.: Works with Firefox 1.0 - 16.0a1
        meta_compat_full = "%s- %s" % (meta_compat_prefix, max_version)
        
        assert (browser_compatible_applications == meta_compat_full or
                browser_compatible_applications == meta_compat_abbrev or
                browser_compatible_applications.startswith(meta_compat_prefix)
                ), "Listed compat. versions don't match versions listed in API."

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_addon_number_of_total_downloads_is_correct(self, mozwebqa):

        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        statistics_page = firebug_page.click_view_statistics()
        browser_downloads = statistics_page.total_downloads_number

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_downloads = addons_xml.get_total_downloads()

        Assert.equal(browser_downloads, xml_downloads)

    @pytest.mark.nondestructive
    def test_that_learn_more_link_is_correct(self, mozwebqa):

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        learn_more_url = addons_xml.get_learn_more_url()

        #browser
        details_page = Details(mozwebqa, self.firebug)
        details_page.get_url(learn_more_url)

        Assert.contains(self.firebug, details_page.page_title)

    @pytest.mark.nondestructive
    def test_that_firebug_devs_comments_is_correct(self, mozwebqa):

        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        firebug_page.expand_devs_comments()
        browser_devs_comments = firebug_page.devs_comments_message

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_devs_comments = addons_xml.get_devs_comments()

        Assert.equal(xml_devs_comments, browser_devs_comments)

    @pytest.mark.nondestructive
    def test_that_home_page_in_api_equals_home_page_in_details_page(self, mozwebqa):

        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        browser_home_page = urlparse.unquote(firebug_page.website)

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_home_page = addons_xml.get_home_page()

        Assert.contains(xml_home_page, browser_home_page)

    @pytest.mark.nondestructive
    def test_that_reviews_in_api_equals_reviews_in_details_page(self, mozwebqa):

        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        browser_reviews = firebug_page.total_reviews_count

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_reviews = addons_xml.get_reviews_count()

        Assert.equal(browser_reviews, xml_reviews)

    @pytest.mark.nondestructive
    def test_that_daily_users_in_api_equals_daily_users_in_details_page(self, mozwebqa):

        #browser
        firebug_page = Details(mozwebqa, self.firebug)
        browser_daily_users = firebug_page.daily_users_number

        #api
        addons_xml = AddonsAPI(mozwebqa, self.firebug)
        xml_daily_users = addons_xml.get_daily_users()

        Assert.equal(browser_daily_users, xml_daily_users)

########NEW FILE########
__FILENAME__ = test_discovery_page
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
from itertools import cycle

import pytest
from unittestzero import Assert

from pages.desktop.discovery import DiscoveryPane
from pages.desktop.home import Home


class TestDiscoveryPane:

    #Need to get this info before run
    def basepath(self, mozwebqa):
        return '/en-US/firefox/discovery/pane/%s/Darwin' % mozwebqa.selenium.capabilities['version']

    @pytest.mark.nondestructive
    def test_that_users_with_less_than_3_addons_get_what_are_addons(self, mozwebqa):
        """
        Since Selenium starts with a clean profile all the time this will always have
        less than 3 addons.
        """
        discovery_pane = DiscoveryPane(mozwebqa, self.basepath(mozwebqa))
        what_are_addons_expected = "Add-ons are applications that let you personalize "
        what_are_addons_expected += "Firefox with extra functionality or style. Try a time-saving"
        what_are_addons_expected += " sidebar, a weather notifier, or a themed look to make "
        what_are_addons_expected += "Firefox your own.\nLearn More"

        Assert.equal(what_are_addons_expected, discovery_pane.what_are_addons_text)

    @pytest.mark.nondestructive
    def test_that_mission_statement_is_on_addons_home_page(self, mozwebqa):
        discovery_pane = DiscoveryPane(mozwebqa, self.basepath(mozwebqa))
        expected_text = "Thanks for using Firefox and supporting Mozilla's mission!"

        mission_text = discovery_pane.mission_section
        Assert.true(expected_text in mission_text)
        Assert.true(discovery_pane.mozilla_org_link_visible())
        download_count_regex = "Add-ons downloaded: (.+)"
        Assert.true(re.search(download_count_regex, discovery_pane.download_count) is not None)

    @pytest.mark.nondestructive
    def test_that_featured_themes_is_present_and_has_5_item(self, mozwebqa):
        discovery_pane = DiscoveryPane(mozwebqa, self.basepath(mozwebqa))
        Assert.true(discovery_pane.is_themes_section_visible)
        Assert.equal(5, discovery_pane.themes_count)
        Assert.true(discovery_pane.is_themes_see_all_link_visible)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_featured_themes_go_to_their_landing_page_when_clicked(self, mozwebqa):
        discovery_pane = DiscoveryPane(mozwebqa, self.basepath(mozwebqa))
        first_theme = discovery_pane.first_theme
        theme = discovery_pane.click_on_first_theme()
        Assert.contains(first_theme, theme.theme_title)

    @pytest.mark.nondestructive
    def test_that_more_ways_to_customize_section_is_available(self, mozwebqa):
        discovery_pane = DiscoveryPane(mozwebqa, self.basepath(mozwebqa))
        Assert.true(discovery_pane.more_ways_section_visible)
        Assert.equal("Browse all add-ons", discovery_pane.browse_all_addons)
        Assert.equal("See all complete themes", discovery_pane.see_all_complete_themes)

    @pytest.mark.nondestructive
    def test_that_up_and_coming_is_present_and_had_5_items(self, mozwebqa):
        discovery_pane = DiscoveryPane(mozwebqa, self.basepath(mozwebqa))
        Assert.equal(5, discovery_pane.up_and_coming_item_count)

    @pytest.mark.nondestructive
    @pytest.mark.login
    def test_the_logout_link_for_logged_in_users(self, mozwebqa):
        home_page = Home(mozwebqa)
        home_page.login()
        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.header.is_user_logged_in)

        discovery_pane = DiscoveryPane(mozwebqa, self.basepath(mozwebqa))
        home_page = discovery_pane.click_logout()
        Assert.true(home_page.is_the_current_page)
        Assert.false(home_page.header.is_user_logged_in)

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_that_carousel_works(self, mozwebqa):
        discovery_pane = DiscoveryPane(mozwebqa, self.basepath(mozwebqa))

        # ensure the first panel is visible
        current_panel = discovery_pane.carousel_panels[1]
        Assert.true(current_panel.is_visible)
        first_heading = current_panel.heading

        # switch to the second panel
        discovery_pane.show_next_carousel_panel()
        current_panel = discovery_pane.carousel_panels[2]
        Assert.not_equal(current_panel.heading, first_heading)
        Assert.true(current_panel.is_visible)

        # switch back to the first panel
        discovery_pane.show_previous_carousel_panel()
        current_panel = discovery_pane.carousel_panels[1]
        Assert.equal(current_panel.heading, first_heading)
        Assert.true(current_panel.is_visible)

    @pytest.mark.nondestructive
    def test_that_cycles_through_all_panels_in_the_carousel(self, mozwebqa):
        discovery_pane = DiscoveryPane(mozwebqa, self.basepath(mozwebqa))
        carousel_panels = discovery_pane.carousel_panels

        # remove first and last panels, they are phantoms!
        carousel_panels.pop(0)
        carousel_panels.pop(-1)
        panels_count = len(carousel_panels)

        # create and init cycle
        panels = cycle(carousel_panels)
        first_heading = panels.next().heading

        # advance forward, check that current panel is visible
        # to ensure that panels are being switched
        for i in range(panels_count):
            discovery_pane.show_next_carousel_panel()
            current_panel = panels.next()
            current_panel.wait_for_next_promo()
            Assert.true(current_panel.heading)
            Assert.true(current_panel.is_visible)

        # now check that current panel has the same heading as
        # the first one to ensure that we have completed the cycle
        last_heading = current_panel.heading
        Assert.equal(first_heading, last_heading)

########NEW FILE########
__FILENAME__ = test_extensions
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from unittestzero import Assert
from pages.desktop.home import Home


class TestExtensions:

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_featured_tab_is_highlighted_by_default(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()
        Assert.equal(featured_extensions_page.sorter.sorted_by, "Featured")

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_pagination(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()
        featured_extensions_page.sorter.sort_by('most_users')
        featured_extensions_page.paginator.click_next_page()

        Assert.contains("&page=2", featured_extensions_page.get_url_current_page())

        featured_extensions_page.paginator.click_prev_page()

        Assert.contains("&page=1", featured_extensions_page.get_url_current_page())

        featured_extensions_page.paginator.click_last_page()

        Assert.true(featured_extensions_page.paginator.is_next_page_disabled)

        featured_extensions_page.paginator.click_first_page()

        Assert.true(featured_extensions_page.paginator.is_prev_page_disabled)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_previous_button_is_disabled_on_the_first_page(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()
        featured_extensions_page.sorter.sort_by('Most Users')

        Assert.true(featured_extensions_page.paginator.is_prev_page_disabled)

        featured_extensions_page.paginator.click_next_page()
        featured_extensions_page.paginator.click_prev_page()

        Assert.true(featured_extensions_page.paginator.is_prev_page_disabled)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_next_button_is_disabled_on_the_last_page(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()
        featured_extensions_page.sorter.sort_by('most_users')
        featured_extensions_page.paginator.click_last_page()

        Assert.true(featured_extensions_page.paginator.is_next_page_disabled, 'Next button is available')

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_checks_if_the_extensions_are_sorted_by_top_rated(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()
        featured_extensions_page.sorter.sort_by("Top Rated")
        Assert.equal(featured_extensions_page.sorter.sorted_by, "Top Rated")
        Assert.contains("sort=rating", featured_extensions_page.get_url_current_page())

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_checks_if_the_extensions_are_sorted_by_most_user(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()
        featured_extensions_page.sorter.sort_by('most_users')

        Assert.contains("sort=users", featured_extensions_page.get_url_current_page())
        user_counts = [extension.user_count for extension in featured_extensions_page.extensions]
        Assert.is_sorted_descending(user_counts)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_checks_if_the_extensions_are_sorted_by_newest(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()
        featured_extensions_page.sorter.sort_by('newest')
        Assert.equal(featured_extensions_page.sorter.sorted_by, "Newest")
        Assert.contains("sort=created", featured_extensions_page.get_url_current_page())

        added_dates = [i.added_date for i in featured_extensions_page.extensions]
        Assert.is_sorted_descending(added_dates)
        featured_extensions_page.paginator.click_next_page()

        added_dates.extend([i.added_date for i in featured_extensions_page.extensions])
        Assert.is_sorted_descending(added_dates)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_checks_if_the_extensions_are_sorted_by_recently_updated(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()

        featured_extensions_page.sorter.sort_by('recently updated')
        Assert.equal(featured_extensions_page.sorter.sorted_by, "Recently Updated")
        Assert.contains("sort=updated", featured_extensions_page.get_url_current_page())

        updated_dates = [i.updated_date for i in featured_extensions_page.extensions]
        Assert.is_sorted_descending(updated_dates)
        featured_extensions_page.paginator.click_next_page()

        updated_dates.extend([i.updated_date for i in featured_extensions_page.extensions])
        Assert.is_sorted_descending(updated_dates)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_extensions_are_sorted_by_up_and_coming(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()

        featured_extensions_page.sorter.sort_by('up and coming')
        Assert.equal(featured_extensions_page.sorter.sorted_by, "Up & Coming")
        Assert.contains("sort=hotness", featured_extensions_page.get_url_current_page())
        Assert.greater(len(featured_extensions_page.extensions), 0)

    @pytest.mark.nondestructive
    def test_that_extensions_page_contains_addons_and_the_pagination_works(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()

        # Assert that at least one addon is displayed
        Assert.greater(len(featured_extensions_page.extensions), 0)

        if len(featured_extensions_page.extensions) < 20:
            # Assert that the paginator is not present if fewer than 20 extensions are displayed
            Assert.false(featured_extensions_page.is_paginator_present)
        else:
            # Assert that the paginator is present if 20 extensions are displayed
            Assert.true(featured_extensions_page.is_paginator_present)
            Assert.true(featured_extensions_page.paginator.is_prev_page_disabled)
            Assert.false(featured_extensions_page.paginator.is_next_page_disabled)

            featured_extensions_page.paginator.click_next_page()

            Assert.false(featured_extensions_page.paginator.is_prev_page_disabled)
            Assert.false(featured_extensions_page.paginator.is_next_page_disabled)

            featured_extensions_page.paginator.click_prev_page()

            Assert.equal(len(featured_extensions_page.extensions), 20)
            Assert.true(featured_extensions_page.paginator.is_prev_page_disabled)
            Assert.false(featured_extensions_page.paginator.is_next_page_disabled)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_breadcrumb_menu_in_extensions_page(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()

        breadcrumbs = featured_extensions_page.breadcrumbs

        Assert.equal(breadcrumbs[0].text, 'Add-ons for Firefox')
        Assert.equal(breadcrumbs[1].text, 'Extensions')

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_checks_if_the_subscribe_link_exists(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()
        Assert.contains("Subscribe", featured_extensions_page.subscribe_link_text)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_checks_featured_extensions_header(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extensions_page = home_page.header.site_navigation_menu("Extensions").click()
        Assert.equal("Featured Extensions", featured_extensions_page.featured_extensions_header_text)

########NEW FILE########
__FILENAME__ = test_homepage
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from unittestzero import Assert

from pages.desktop.home import Home


class HeaderMenu:

    def __init__(self, name, items):
        self.name = name
        self.items = items

    @property
    def name(self):
        return self.name

    @property
    def items(self):
        return self.items


class TestHome:

    expected_header_menus = [
        HeaderMenu('EXTENSIONS', [
            "Featured", "Most Popular", "Top Rated", "Alerts & Updates", "Appearance", "Bookmarks",
            "Download Management", "Feeds, News & Blogging", "Games & Entertainment",
            "Language Support", "Photos, Music & Videos", "Privacy & Security", "Search Tools", "Shopping",
            "Social & Communication", "Tabs", "Web Development", "Other"]),
        HeaderMenu('THEMES', [
            "Most Popular", "Top Rated", "Newest", "Abstract", "Causes", "Fashion", "Film and TV",
            "Firefox", "Foxkeh", "Holiday", "Music", "Nature", "Other", "Scenery", "Seasonal",
            "Solid", "Sports", "Websites"]),
        HeaderMenu('COLLECTIONS', [
            "Featured", "Most Followers", "Newest", "Collections I've Made",
            "Collections I'm Following", "My Favorite Add-ons"]),
        HeaderMenu(u'MORE\u2026', [
            "Add-ons for Mobile", "Dictionaries & Language Packs", "Search Tools", "Developer Hub"])]

    @pytest.mark.nondestructive
    def test_that_checks_the_most_popular_section_exists(self, mozwebqa):
        home_page = Home(mozwebqa)
        Assert.contains('MOST POPULAR', home_page.most_popular_list_heading)
        Assert.equal(home_page.most_popular_count, 10)

    @pytest.mark.nondestructive
    def test_that_checks_the_promo_box_exists(self, mozwebqa):
        home_page = Home(mozwebqa)
        Assert.true(home_page.promo_box_present)

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_that_clicking_on_addon_name_loads_details_page(self, mozwebqa):
        home_page = Home(mozwebqa)
        details_page = home_page.click_on_first_addon()
        Assert.true(details_page.is_the_current_page)

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_that_featured_themes_exist_on_the_home(self, mozwebqa):
        home_page = Home(mozwebqa)
        Assert.equal(home_page.featured_themes_title, u'Featured Themes See all \xbb', 'Featured Themes region title doesn\'t match')
        Assert.greater_equal(home_page.featured_themes_count, 6)

    @pytest.mark.nondestructive
    def test_that_clicking_see_all_themes_link_works(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_theme_page = home_page.click_featured_themes_see_all_link()

        Assert.true(featured_theme_page.is_the_current_page)
        Assert.equal(featured_theme_page.theme_header, 'Themes')

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_extensions_link_loads_extensions_page(self, mozwebqa):
        home_page = Home(mozwebqa)
        extensions_page = home_page.header.site_navigation_menu("EXTENSIONS").click()
        Assert.true(extensions_page.is_the_current_page)

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_that_most_popular_section_is_ordered_by_users(self, mozwebqa):
        home_page = Home(mozwebqa)

        most_popular_items = home_page.most_popular_items
        Assert.is_sorted_descending([i.users_number for i in most_popular_items])

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_that_featured_collections_exist_on_the_home(self, mozwebqa):
        home_page = Home(mozwebqa)
        Assert.equal(home_page.featured_collections_title, u'Featured Collections See all \xbb', 'Featured Collection region title doesn\'t match')
        Assert.equal(home_page.featured_collections_count, 4)

    @pytest.mark.nondestructive
    def test_that_featured_extensions_exist_on_the_home(self, mozwebqa):
        home_page = Home(mozwebqa)
        Assert.equal(home_page.featured_extensions_title, 'Featured Extensions', 'Featured Extensions region title doesn\'t match')
        Assert.equal(home_page.featured_extensions_see_all, u'See all \xbb', 'Featured Extensions region see all link is not correct')
        Assert.greater(home_page.featured_extensions_count, 1)

    @pytest.mark.nondestructive
    def test_that_clicking_see_all_collections_link_works(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_collection_page = home_page.click_featured_collections_see_all_link()
        Assert.true(featured_collection_page.is_the_current_page)
        Assert.true(featured_collection_page.get_url_current_page().endswith('/collections/?sort=featured'))

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_that_items_menu_fly_out_while_hovering(self, mozwebqa):

        #I've adapted the test to check open/closed for all menu items
        home_page = Home(mozwebqa)

        for menu in self.expected_header_menus:
            menu_item = home_page.header.site_navigation_menu(menu.name)
            menu_item.hover()
            Assert.true(menu_item.is_menu_dropdown_visible)
            home_page.hover_over_addons_home_title()
            Assert.false(menu_item.is_menu_dropdown_visible)

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_that_clicking_top_rated_shows_addons_sorted_by_rating(self, mozwebqa):
        home_page = Home(mozwebqa)
        extensions_page = home_page.click_to_explore('top_rated')

        Assert.contains('sort=rating', extensions_page.get_url_current_page())
        Assert.equal('Top Rated', extensions_page.sorter.sorted_by)

    @pytest.mark.nondestructive
    def test_that_clicking_most_popular_shows_addons_sorted_by_users(self, mozwebqa):
        home_page = Home(mozwebqa)
        extensions_page = home_page.click_to_explore('popular')

        Assert.contains('sort=users', extensions_page.get_url_current_page())
        Assert.equal('Most Users', extensions_page.sorter.sorted_by)

    @pytest.mark.nondestructive
    def test_that_clicking_featured_shows_addons_sorted_by_featured(self, mozwebqa):
        home_page = Home(mozwebqa)
        extensions_page = home_page.click_to_explore('featured')

        Assert.contains('sort=featured', extensions_page.get_url_current_page())
        Assert.equal('Featured', extensions_page.sorter.sorted_by)

    @pytest.mark.nondestructive
    def test_header_site_navigation_menus_are_correct(self, mozwebqa):
        home_page = Home(mozwebqa)

        # compile lists of the expected and actual top level navigation items
        expected_navigation_menu = [menu.name for menu in self.expected_header_menus]
        actual_navigation_menus = [actual_menu.name for actual_menu in home_page.header.site_navigation_menus]

        Assert.equal(expected_navigation_menu, actual_navigation_menus)

    @pytest.mark.action_chains
    @pytest.mark.nondestructive
    def test_the_name_of_each_site_navigation_menu_in_the_header(self, mozwebqa):
        home_page = Home(mozwebqa)

        # loop through each expected menu and collect a list of the items in the menu
        # and then assert that they exist in the actual menu on the page
        for menu in self.expected_header_menus:
            expected_menu_items = menu.items
            actual_menu_items = [menu_items.name for menu_items in home_page.header.site_navigation_menu(menu.name).items]

            Assert.equal(expected_menu_items, actual_menu_items)

    @pytest.mark.nondestructive
    def test_top_three_items_in_each_site_navigation_menu_are_featured(self, mozwebqa):
        home_page = Home(mozwebqa)

        # loop through each actual top level menu
        for actual_menu in home_page.header.site_navigation_menus:
            # 'more' navigation_menu has no featured items so we have a different assertion
            if actual_menu.name == u"MORE\u2026":
                # loop through each of the items in the top level menu and check is_featured property
                [Assert.false(item.is_featured) for item in actual_menu.items]
            else:
                # first 3 are featured, the others are not
                [Assert.true(item.is_featured) for item in actual_menu.items[:3]]
                [Assert.false(item.is_featured) for item in actual_menu.items[3:]]

    @pytest.mark.nondestructive
    def test_that_checks_the_up_and_coming_extensions_island(self, mozwebqa):

        home_page = Home(mozwebqa)

        up_and_coming_island = home_page.up_and_coming_island

        Assert.equal(up_and_coming_island.title, 'Up & Coming Extensions')
        Assert.equal(up_and_coming_island.see_all_text, u'See all \xbb')

        for idx in range(up_and_coming_island.pager.dot_count):
            Assert.equal(idx, up_and_coming_island.visible_section)
            Assert.equal(idx, up_and_coming_island.pager.selected_dot)
            Assert.equal(len(up_and_coming_island.addons), 6)
            up_and_coming_island.pager.next()

        for idx in range(up_and_coming_island.pager.dot_count - 1, -1, -1):
            Assert.equal(idx, up_and_coming_island.visible_section)
            Assert.equal(idx, up_and_coming_island.pager.selected_dot)
            Assert.equal(len(up_and_coming_island.addons), 6)
            up_and_coming_island.pager.prev()

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_addons_author_link(self, mozwebqa):

        home_page = Home(mozwebqa)
        first_addon = home_page.featured_extensions[0]

        first_author = first_addon.author_name
        user_page = first_addon.click_first_author()

        Assert.equal(user_page.username, first_author[0])
        Assert.contains('user', user_page.get_url_current_page())

    def test_that_checks_explore_side_navigation(self, mozwebqa):
        home_page = Home(mozwebqa)

        Assert.equal('EXPLORE', home_page.explore_side_navigation_header_text)
        Assert.equal('Featured', home_page.explore_featured_link_text)
        Assert.equal('Most Popular', home_page.explore_popular_link_text)
        Assert.equal('Top Rated', home_page.explore_top_rated_link_text)

    @pytest.mark.nondestructive
    def test_that_clicking_see_all_extensions_link_works(self, mozwebqa):
        home_page = Home(mozwebqa)
        featured_extension_page = home_page.click_featured_extensions_see_all_link()
        Assert.true(featured_extension_page.is_the_current_page)
        Assert.true(featured_extension_page.get_url_current_page().endswith('/extensions/?sort=featured'))

    @pytest.mark.nondestructive
    def test_that_checks_all_categories_side_navigation(self, mozwebqa):
        home_page = Home(mozwebqa)
        category_region = home_page.get_category()

        Assert.equal('CATEGORIES', category_region.categories_side_navigation_header_text)
        Assert.equal('Alerts & Updates', category_region.categories_alert_updates_header_text)
        Assert.equal('Appearance', category_region.categories_appearance_header_text)
        Assert.equal('Bookmarks', category_region.categories_bookmark_header_text)
        Assert.equal('Download Management', category_region.categories_download_management_header_text)
        Assert.equal('Feeds, News & Blogging', category_region.categories_feed_news_blog_header_text)
        Assert.equal('Games & Entertainment', category_region.categories_games_entertainment_header_text)
        Assert.equal('Language Support', category_region.categories_language_support_header_text)
        Assert.equal('Photos, Music & Videos', category_region.categories_photo_music_video_header_text)
        Assert.equal('Privacy & Security', category_region.categories_privacy_security_header_text)
        Assert.equal('Shopping', category_region.categories_shopping_header_text)
        Assert.equal('Social & Communication', category_region.categories_social_communication_header_text)
        Assert.equal('Tabs', category_region.categories_tabs_header_text)
        Assert.equal('Web Development', category_region.categories_web_development_header_text)
        Assert.equal('Other', category_region.categories_other_header_text)

########NEW FILE########
__FILENAME__ = test_installs
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import pytest

from unittestzero import Assert

from pages.desktop.home import Home


class TestInstalls:

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_could_install_theme(self, mozwebqa):
        """note that this test does not actually *install* the theme"""

        home_page = Home(mozwebqa)
        complete_themes_page = home_page.header.click_complete_themes()
        complete_theme_page = complete_themes_page.click_on_first_addon()
        Assert.true(complete_theme_page.install_button_exists)

    @pytest.mark.nondestructive
    def test_could_install_jetpack(self, mozwebqa):
        """note that this test does not actually *install* the jetpack"""

        home_page = Home(mozwebqa)
        search_page = home_page.search_for("jetpack")
        for result in search_page.results:
            # click on the first compatible result
            if result.is_compatible:
                details_page = result.click_result()
                break

        Assert.true(details_page.is_version_information_install_button_visible)

########NEW FILE########
__FILENAME__ = test_layout
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from unittestzero import Assert

from pages.desktop.home import Home


class TestAmoLayout:

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_other_applications_thunderbird(self, mozwebqa):
        app_under_test = "Thunderbird"
        home_page = Home(mozwebqa)

        home_page.header.click_other_application(app_under_test)
        Assert.contains(app_under_test.lower(), home_page.get_url_current_page())

        Assert.false(home_page.header.is_other_application_visible(app_under_test))

    @pytest.mark.nondestructive
    def test_that_checks_amo_logo_text_layout_and_title(self, mozwebqa):
        home_page = Home(mozwebqa)
        Assert.equal(home_page.amo_logo_text, "ADD-ONS")
        Assert.equal(home_page.amo_logo_title, "Return to the Firefox Add-ons homepage")
        Assert.contains("-cdn.allizom.org/media/img/app-icons/med/firefox.png", home_page.amo_logo_image_source)

    @pytest.mark.nondestructive
    def test_that_clicking_the_amo_logo_loads_home_page(self, mozwebqa):
        home_page = Home(mozwebqa)

        Assert.true(home_page.is_amo_logo_visible)
        home_page = home_page.click_amo_logo()
        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.is_amo_logo_visible)
        Assert.equal(home_page.get_url_current_page(), '%s/en-US/firefox/' % home_page.base_url)

    @pytest.mark.nondestructive
    def test_that_other_applications_link_has_tooltip(self, mozwebqa):
        home_page = Home(mozwebqa)
        tooltip = home_page.get_title_of_link('Other applications')
        Assert.equal(tooltip, 'Find add-ons for other applications')

    @pytest.mark.action_chains
    @pytest.mark.nondestructive
    @pytest.mark.parametrize('expected_app', ["Thunderbird", "Android", "SeaMonkey"])
    def test_the_applications_listed_in_other_applications(self, mozwebqa, expected_app):
        home_page = Home(mozwebqa)

        Assert.true(home_page.header.is_other_application_visible(expected_app),
                "%s link not found in the Other Applications menu" % expected_app)

    @pytest.mark.nondestructive
    def test_the_search_field_placeholder_and_search_button(self, mozwebqa):
        home_page = Home(mozwebqa)
        Assert.equal(home_page.header.search_field_placeholder, 'search for add-ons')
        Assert.true(home_page.header.is_search_button_visible)
        Assert.equal(home_page.header.search_button_title, 'Search')

    @pytest.mark.nondestructive
    def test_the_search_box_exist(self, mozwebqa):
        home_page = Home(mozwebqa)
        Assert.true(home_page.header.is_search_textbox_visible)

########NEW FILE########
__FILENAME__ = test_paypal
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import pytest

from unittestzero import Assert

from pages.desktop.home import Home
from pages.desktop.details import Details


class TestPaypal:

    addon_name = 'Firebug'

    @pytest.mark.login
    def test_that_user_can_contribute_to_an_addon(self, mozwebqa):
        """Test that checks the Contribute button for an add-on using PayPal."""

        addon_page = Home(mozwebqa)

        addon_page.login()
        Assert.true(addon_page.is_the_current_page)
        Assert.true(addon_page.header.is_user_logged_in)

        addon_page = Details(mozwebqa, self.addon_name)

        contribution_snippet = addon_page.click_contribute_button()
        paypal_frame = contribution_snippet.click_make_contribution_button()
        Assert.true(addon_page.is_paypal_login_dialog_visible)

        payment_popup = paypal_frame.login_to_paypal(user="paypal")
        Assert.true(payment_popup.is_user_logged_into_paypal)
        payment_popup.click_pay()
        Assert.true(payment_popup.is_payment_successful)
        payment_popup.close_paypal_popup()
        Assert.true(addon_page.is_the_current_page)

    @pytest.mark.login
    def test_that_user_can_make_a_contribution_without_logging_into_amo(self, mozwebqa):
        """Test that checks if the user is able to make a contribution without logging in to AMO."""
        addon_page = Details(mozwebqa, self.addon_name)
        Assert.false(addon_page.header.is_user_logged_in)

        contribution_snippet = addon_page.click_contribute_button()
        paypal_frame = contribution_snippet.click_make_contribution_button()
        Assert.true(addon_page.is_paypal_login_dialog_visible)

        payment_popup = paypal_frame.login_to_paypal(user="paypal")
        Assert.true(payment_popup.is_user_logged_into_paypal)
        payment_popup.click_pay()
        Assert.true(payment_popup.is_payment_successful)
        payment_popup.close_paypal_popup()
        Assert.true(addon_page.is_the_current_page)

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_that_make_contribution_button_is_clickable_and_loads_paypal_frame_while_user_is_logged_out(self, mozwebqa):
        addon_page = Details(mozwebqa, self.addon_name)
        Assert.false(addon_page.header.is_user_logged_in)

        contribution_snippet = addon_page.click_contribute_button()

        Assert.true(contribution_snippet.is_make_contribution_button_visible)
        Assert.equal("Make Contribution", contribution_snippet.make_contribution_button_name)

        contribution_snippet.click_make_contribution_button()
        Assert.true(addon_page.is_paypal_login_dialog_visible)

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    @pytest.mark.login
    def test_that_make_contribution_button_is_clickable_and_loads_paypal_frame_while_user_is_logged_in(self, mozwebqa):
        addon_page = Details(mozwebqa, self.addon_name)
        addon_page.login()
        Assert.true(addon_page.is_the_current_page)
        Assert.true(addon_page.header.is_user_logged_in)

        contribution_snippet = addon_page.click_contribute_button()

        Assert.true(contribution_snippet.is_make_contribution_button_visible)
        Assert.equal("Make Contribution", contribution_snippet.make_contribution_button_name)

        contribution_snippet.click_make_contribution_button()
        Assert.true(addon_page.is_paypal_login_dialog_visible)

########NEW FILE########
__FILENAME__ = test_reviews
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from datetime import datetime
from unittestzero import Assert

from pages.desktop.home import Home
from pages.desktop.details import Details


class TestReviews:

    @pytest.mark.nondestructive
    def test_that_all_reviews_hyperlink_works(self, mozwebqa):
        #Open details page for MemChaser
        details_page = Details(mozwebqa, "Firebug")
        Assert.true(details_page.has_reviews)

        view_reviews = details_page.click_all_reviews_link()
        Assert.equal(len(view_reviews.reviews), 20)

        #Go to the last page and check that the next button is not present
        view_reviews.paginator.click_last_page()
        Assert.true(view_reviews.paginator.is_next_page_disabled)

        #Go one page back, check that it has 20 reviews
        #that the page number decreases and that the next link is visible
        page_number = view_reviews.paginator.page_number
        view_reviews.paginator.click_prev_page()
        Assert.false(view_reviews.paginator.is_next_page_disabled)
        Assert.equal(len(view_reviews.reviews), 20)
        Assert.equal(view_reviews.paginator.page_number, page_number - 1)

        #Go to the first page and check that the prev button is not present
        view_reviews.paginator.click_first_page()
        Assert.true(view_reviews.paginator.is_prev_page_disabled)

        #Go one page forward, check that it has 20 reviews,
        #that the page number increases and that the prev link is visible
        page_number = view_reviews.paginator.page_number
        view_reviews.paginator.click_next_page()
        Assert.false(view_reviews.paginator.is_prev_page_disabled)
        Assert.equal(len(view_reviews.reviews), 20)
        Assert.equal(view_reviews.paginator.page_number, page_number + 1)

    @pytest.mark.native
    @pytest.mark.login
    def test_that_new_review_is_saved(self, mozwebqa):
        # Step 1 - Login into AMO
        home_page = Home(mozwebqa)
        home_page.login()
        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.header.is_user_logged_in)

        # Step 2 - Load any addon detail page
        details_page = Details(mozwebqa, 'Memchaser')

        # Step 3 - Click on "Write review" button
        write_review_block = details_page.click_to_write_review()

        # Step 4 - Write a review
        body = 'Automatic addon review by Selenium tests %s' % datetime.now()
        write_review_block.enter_review_with_text(body)
        write_review_block.set_review_rating(1)
        review_page = write_review_block.click_to_save_review()

        # Step 5 - Assert review
        review = review_page.reviews[0]
        Assert.equal(review.rating, 1)
        Assert.equal(review.author, mozwebqa.credentials['default']['name'])
        date = datetime.now().strftime("%B %d, %Y")
        # there are no leading zero-signs on day so we need to remove them too
        date = date.replace(' 0', ' ')
        Assert.equal(review.date, date)
        Assert.equal(review.text, body)

        review.delete()

        details_page = Details(mozwebqa, 'Memchaser')
        review_page = details_page.click_all_reviews_link()

        for review in review_page.reviews:
            Assert.false(body in review.text)

########NEW FILE########
__FILENAME__ = test_search
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import pytest

from unittestzero import Assert

from pages.desktop.home import Home


class TestSearch:

    @pytest.mark.nondestructive
    def test_that_search_all_add_ons_results_have_pagination_that_moves_through_results(self, mozwebqa):
        """
        Open a page with search results.
        1. On the first page, check that "<<" and "previous are not active, but "next" and ">>" are active.
        2. Move forward one page by clicking next, all buttons are active
        3. Click ">>" to go to last page.  Check that "<<" and "previous" are clickable but "next" and ">>" are not.
        4. Assert the page number has incremented or decreased
        5. Click "previous", all buttons are highlighted.
        """
        home_page = Home(mozwebqa)
        search_page = home_page.search_for('addon')

        expected_page = 1

        # On the first page, "<<" and "previous" are not active, but "next" and ">>" are active.
        Assert.true(search_page.paginator.is_prev_page_disabled)
        Assert.true(search_page.paginator.is_first_page_disabled)
        Assert.false(search_page.paginator.is_next_page_disabled)
        Assert.false(search_page.paginator.is_last_page_disabled)
        Assert.equal(search_page.paginator.page_number, expected_page)

        # Move forward one page by clicking next, all buttons should be active.
        search_page.paginator.click_next_page()

        expected_page += 1

        Assert.false(search_page.paginator.is_prev_page_disabled)
        Assert.false(search_page.paginator.is_first_page_disabled)
        Assert.false(search_page.paginator.is_next_page_disabled)
        Assert.false(search_page.paginator.is_last_page_disabled)
        Assert.equal(search_page.paginator.page_number, expected_page)

        # Click ">>" to go to last page. "<<" and "previous" are active, but "next" and ">>" are not.
        search_page.paginator.click_last_page()

        expected_page = search_page.paginator.total_page_number

        Assert.false(search_page.paginator.is_prev_page_disabled)
        Assert.false(search_page.paginator.is_first_page_disabled)
        Assert.true(search_page.paginator.is_next_page_disabled)
        Assert.true(search_page.paginator.is_last_page_disabled)
        Assert.equal(search_page.paginator.page_number, expected_page)

        # Click "previous", all buttons are active.
        search_page.paginator.click_prev_page()

        expected_page -= 1

        Assert.false(search_page.paginator.is_prev_page_disabled)
        Assert.false(search_page.paginator.is_first_page_disabled)
        Assert.false(search_page.paginator.is_next_page_disabled)
        Assert.false(search_page.paginator.is_last_page_disabled)
        Assert.equal(search_page.paginator.page_number, expected_page)

    @pytest.mark.nondestructive
    @pytest.mark.parametrize('term', [
        # 9575
        u'\u0421\u043b\u043e\u0432\u0430\u0440\u0438 \u042f\u043d\u0434\u0435\u043a\u0441',
        'fox',  # 9561
        '',     # 11759
        '1',    # 17347
    ])
    def test_that_various_search_terms_return_results(self, mozwebqa, term):
        search_page = Home(mozwebqa).search_for(term)

        Assert.false(search_page.is_no_results_present)
        Assert.greater(search_page.result_count, 0)

    @pytest.mark.nondestructive
    def test_that_page_with_search_results_has_correct_title(self, mozwebqa):
        home_page = Home(mozwebqa)
        search_keyword = 'Search term'
        search_page = home_page.search_for(search_keyword)

        expected_title = '%s :: Search :: Add-ons for Firefox' % search_keyword
        Assert.equal(expected_title, search_page.page_title)

    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_that_searching_for_firebug_returns_firebug_as_first_result(self, mozwebqa):
        home_page = Home(mozwebqa)
        search_page = home_page.search_for('firebug')
        results = [result.name for result in search_page.results]

        Assert.equal('Firebug', results[0])

    @pytest.mark.nondestructive
    def test_that_searching_for_cool_returns_results_with_cool_in_their_name_description(self, mozwebqa):
        home_page = Home(mozwebqa)
        search_term = 'cool'
        search_page = home_page.search_for(search_term)
        Assert.false(search_page.is_no_results_present)

        for i in range(0, len(search_page.results)):
            try:
                Assert.contains(search_term, search_page.results[i].text.lower())
            except:
                devs_comments = ''
                details_page = search_page.results[i].click_result()
                if details_page.is_devs_comments_section_present:
                    details_page.expand_devs_comments()
                    devs_comments = details_page.devs_comments_message
                search_range = details_page.description + devs_comments
                Assert.contains(search_term, search_range.lower())
                details_page.return_to_previous_page()

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_sorting_by_downloads(self, mozwebqa):
        search_page = Home(mozwebqa).search_for('firebug')
        search_page.click_sort_by('Weekly Downloads')
        Assert.true('sort=downloads' in search_page.get_url_current_page())
        downloads = [i.downloads for i in search_page.results]
        Assert.is_sorted_descending(downloads)
        search_page.paginator.click_next_page()

        downloads.extend([i.downloads for i in search_page.results])
        Assert.is_sorted_descending(downloads)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_sorting_by_newest(self, mozwebqa):
        search_page = Home(mozwebqa).search_for('firebug')
        search_page.click_sort_by('Newest')
        Assert.true('sort=created' in search_page.get_url_current_page())
        Assert.is_sorted_descending([i.created_date for i in search_page.results])

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_sorting_by_most_recently_updated(self, mozwebqa):
        search_page = Home(mozwebqa).search_for('firebug')
        search_page.click_sort_by('Recently Updated')
        Assert.contains('sort=updated', search_page.get_url_current_page())
        results = [i.updated_date for i in search_page.results]
        Assert.is_sorted_descending(results)
        search_page.paginator.click_next_page()
        results.extend([i.updated_date for i in search_page.results])
        Assert.is_sorted_descending(results)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_sorting_by_number_of_most_users(self, mozwebqa):
        search_page = Home(mozwebqa).search_for('firebug')
        search_page.click_sort_by('Most Users')
        Assert.contains('sort=users', search_page.get_url_current_page())
        Assert.is_sorted_descending([i.users for i in search_page.results])

    @pytest.mark.nondestructive
    def test_that_searching_for_a_tag_returns_results(self, mozwebqa):

        home_page = Home(mozwebqa)
        search_page = home_page.search_for('development')
        result_count = search_page.filter.results_count
        Assert.greater(result_count, 0)

        search_page.filter.tag('development').click_tag()
        Assert.greater_equal(result_count, search_page.filter.results_count)

    @pytest.mark.nondestructive
    def test_that_search_results_return_20_results_per_page(self, mozwebqa):
        home_page = Home(mozwebqa)
        search_page = home_page.search_for('deutsch')

        first_expected = 1
        second_expected = 20

        while not search_page.paginator.is_next_page_disabled:
            first_count = search_page.paginator.start_item
            second_count = search_page.paginator.end_item

            Assert.equal(first_expected, first_count)
            Assert.equal(second_expected, second_count)
            Assert.equal(search_page.result_count, 20)

            search_page.paginator.click_next_page()

            first_expected += 20
            second_expected += 20

        number = search_page.paginator.total_items % 20

        if number == 0:
            Assert.equal(search_page.result_count, 20)
        else:
            Assert.equal(search_page.result_count, number)

    @pytest.mark.native
    @pytest.mark.nondestructive
    @pytest.mark.smoke
    @pytest.mark.parametrize(('addon_type', 'term', 'breadcrumb_component'), [
        ('Complete Themes', 'glow', 'Complete Themes'),           # 17350
        ('Extensions', 'fire', 'Extensions'),
        ('Themes', 'fox', 'Themes'),        # 17349
        ('Collections', 'web', 'Collections'),  # 17352
        # these last two depend on the More menu
        # ('Add-ons for Mobile', 'fire', 'Extensions')
        # ('Dictionaries & Language Packs', 'a', 'Dictionaries'),
    ])
    def test_searching_for_addon_type_returns_results_of_correct_type(
        self, mozwebqa, addon_type, term, breadcrumb_component
    ):
        amo_home_page = Home(mozwebqa)

        if (addon_type == 'Complete Themes'):
            # Complete Themes are in a subnav, so must be clicked differently
            amo_addon_type_page = amo_home_page.header.click_complete_themes()
        else:
            amo_addon_type_page = amo_home_page.header.site_navigation_menu(addon_type).click()
        search_results = amo_addon_type_page.search_for(term)

        Assert.true(search_results.result_count > 0)

        for i in range(search_results.result_count):
            addon = search_results.result(i).click_result()
            Assert.contains(breadcrumb_component, addon.breadcrumb)
            addon.return_to_previous_page()

########NEW FILE########
__FILENAME__ = test_statistics
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from urlparse import urlparse
from datetime import datetime, timedelta
import json

import requests
import pytest
from unittestzero import Assert

from pages.desktop.details import Details


class TestStatistics:

    @pytest.mark.nondestructive
    def test_that_verifies_the_url_of_the_statistics_page(self, mozwebqa):

        details_page = Details(mozwebqa, "Firebug")
        statistics_page = details_page.click_view_statistics()

        Assert.true(statistics_page.is_the_current_page)
        Assert.contains("/statistics", statistics_page.get_url_current_page())

    @pytest.mark.skipif('urlparse(config.getvalue("base_url")).netloc != "addons.mozilla.org"',
                        reason='Insufficient data on dev/stage')
    @pytest.mark.skip_selenium
    @pytest.mark.nondestructive
    def test_that_checks_content_in_json_endpoints_from_statistics_urls(self, mozwebqa):
        """https://github.com/mozilla/Addon-Tests/issues/621"""

        # make statistics url template
        base_url = mozwebqa.base_url
        temp_url = '/firefox/addon/firebug/statistics/overview-day-%(start)s-%(end)s.json'
        statistics_url_template = base_url + temp_url

        # set statistics timeframe
        last_date = datetime.today().date() - timedelta(days=1)
        first_date = datetime.today().date() - timedelta(days=30)

        # convert datetime objects to required string representation
        end = str(last_date).replace('-', '')
        start = str(first_date).replace('-', '')

        # make request and assert that status code is OK
        r = requests.get(statistics_url_template % locals())
        Assert.equal(r.status_code, 200,
                     'request to %s failed with %s status code' % (r.url, r.status_code))

        # decode response and assert it's not empty
        response = json.loads(r.content)
        Assert.equal(len(response), 30,
                     'some dates (or all) dates are missing in response')

        dates = []
        for value in response:
            dates.append(value['date'])
            downloads, updates = value['data'].values()
            # check that download and update values are equal or greater than zero
            Assert.greater_equal(downloads, 0)
            Assert.greater_equal(updates, 0)

        # ensure that response contains all dates for given timeframe
        Assert.equal(dates, [str(last_date - timedelta(days=i)) for i in xrange(30)],
                     'wrong dates in response')

########NEW FILE########
__FILENAME__ = test_themes
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import random
import pytest

from unittestzero import Assert

from pages.desktop.home import Home


class TestThemes:

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_start_exploring_link_in_the_promo_box(self, mozwebqa):
        home_page = Home(mozwebqa)
        themes_page = home_page.header.site_navigation_menu("Themes").click()
        Assert.true(themes_page.is_the_current_page)
        Assert.true(themes_page.is_featured_addons_present)
        browse_themes_page = themes_page.click_start_exploring()
        Assert.true(browse_themes_page.is_the_current_page)
        Assert.equal("up-and-coming", browse_themes_page.sort_key)
        Assert.equal("Up & Coming", browse_themes_page.sort_by)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_page_title_for_themes_landing_page(self, mozwebqa):
        home_page = Home(mozwebqa)
        themes_page = home_page.header.site_navigation_menu("Themes").click()
        Assert.true(themes_page.is_the_current_page)

    @pytest.mark.native
    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_the_featured_themes_section(self, mozwebqa):
        home_page = Home(mozwebqa)
        themes_page = home_page.header.site_navigation_menu("Themes").click()
        Assert.true(themes_page.is_the_current_page)
        Assert.less_equal(themes_page.featured_themes_count, 6)

    @pytest.mark.native
    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_the_recently_added_section(self, mozwebqa):
        home_page = Home(mozwebqa)
        themes_page = home_page.header.site_navigation_menu("Themes").click()
        Assert.true(themes_page.is_the_current_page)
        Assert.equal(6, themes_page.recently_added_count)
        recently_added_dates = themes_page.recently_added_dates
        Assert.is_sorted_descending(recently_added_dates)

    @pytest.mark.native
    @pytest.mark.smoke
    @pytest.mark.nondestructive
    def test_the_most_popular_section(self, mozwebqa):
        home_page = Home(mozwebqa)
        themes_page = home_page.header.site_navigation_menu("Themes").click()
        Assert.true(themes_page.is_the_current_page)
        Assert.equal(6, themes_page.most_popular_count)
        downloads = themes_page.most_popular_downloads
        Assert.is_sorted_descending(downloads)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_the_top_rated_section(self, mozwebqa):
        home_page = Home(mozwebqa)
        themes_page = home_page.header.site_navigation_menu("Themes").click()
        Assert.true(themes_page.is_the_current_page)
        Assert.equal(6, themes_page.top_rated_count)
        ratings = themes_page.top_rated_ratings
        Assert.is_sorted_descending(ratings)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_breadcrumb_menu_in_theme_details_page(self, mozwebqa):

        # Step 1, 2: Access AMO Home, Click on theme category link.
        home_page = Home(mozwebqa)
        themes_page = home_page.header.site_navigation_menu("Themes").click()
        Assert.true(themes_page.is_the_current_page)

        # Step 3: Click on any theme.
        random_theme_index = random.randint(1, themes_page.theme_count - 1)

        themes_detail_page = themes_page.click_theme(random_theme_index)
        Assert.true(themes_detail_page.is_the_current_page)

        # Verify breadcrumb menu format, i.e. Add-ons for Firefox > themes > {theme Name}.
        theme_title = themes_detail_page.title
        Assert.equal("Add-ons for Firefox", themes_detail_page.breadcrumbs[0].text)
        Assert.equal("Themes", themes_detail_page.breadcrumbs[1].text)

        theme_breadcrumb_title = len(theme_title) > 40 and '%s...' % theme_title[:40] or theme_title

        Assert.equal(themes_detail_page.breadcrumbs[2].text, theme_breadcrumb_title)

        # Step 4: Click on the links present in the Breadcrumb menu.
        # Verify that the themes link loads the themes home page.
        themes_detail_page.breadcrumbs[1].click()
        Assert.true(themes_page.is_the_current_page)

        themes_page.return_to_previous_page()
        Assert.true(themes_detail_page.is_the_current_page)

        # Verify that the Add-ons for Firefox link loads the AMO home page.
        themes_detail_page.breadcrumbs[0].click()
        Assert.true(home_page.is_the_current_page)

    @pytest.mark.native
    @pytest.mark.nondestructive
    def test_themes_breadcrumb_format(self, mozwebqa):
        home_page = Home(mozwebqa)

        themes_page = home_page.header.site_navigation_menu("Themes").click()
        Assert.equal(themes_page.breadcrumbs[0].text, 'Add-ons for Firefox')
        Assert.equal(themes_page.breadcrumbs[1].text, 'Themes')

########NEW FILE########
__FILENAME__ = test_users_account
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
import random
from copy import deepcopy

from unittestzero import Assert

from pages.desktop.home import Home


class TestAccounts:

    @pytest.mark.nondestructive
    @pytest.mark.login
    @pytest.mark.native
    def test_user_can_login_and_logout_using_normal_login(self, mozwebqa):

        home_page = Home(mozwebqa)
        home_page.login("normal")
        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.header.is_user_logged_in)

        home_page.header.click_logout()
        Assert.false(home_page.header.is_user_logged_in)

    @pytest.mark.nondestructive
    @pytest.mark.login
    def test_user_can_login_and_logout_using_browser_id(self, mozwebqa):

        home_page = Home(mozwebqa)
        home_page.login("browserID")
        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.header.is_user_logged_in)

        home_page.header.click_logout()
        Assert.false(home_page.header.is_user_logged_in)

    @pytest.mark.native
    @pytest.mark.nondestructive
    @pytest.mark.login
    def test_user_can_access_the_edit_profile_page(self, mozwebqa):

        home_page = Home(mozwebqa)
        home_page.login()
        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.header.is_user_logged_in)

        amo_user_edit_page = home_page.header.click_edit_profile()
        Assert.contains("/users/edit", amo_user_edit_page.get_url_current_page())
        Assert.true(amo_user_edit_page.is_the_current_page)

        Assert.equal("My Account", amo_user_edit_page.account_header_text)
        Assert.equal("Profile", amo_user_edit_page.profile_header_text)
        Assert.equal("Details", amo_user_edit_page.details_header_text)
        Assert.equal("Notifications", amo_user_edit_page.notification_header_text)

    @pytest.mark.native
    @pytest.mark.nondestructive
    @pytest.mark.login
    def test_user_can_access_the_view_profile_page(self, mozwebqa):

        home_page = Home(mozwebqa)
        home_page.login()
        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.header.is_user_logged_in)

        view_profile_page = home_page.header.click_view_profile()

        Assert.equal(view_profile_page.about_me, 'About me')

    @pytest.mark.native
    @pytest.mark.login
    def test_hide_email_checkbox_works(self, mozwebqa):
        home_page = Home(mozwebqa)
        home_page.login()

        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.header.is_user_logged_in)

        view_profile_page = home_page.header.click_view_profile()
        initial_state = view_profile_page.is_email_field_present

        edit_profile_page = home_page.header.click_edit_profile()
        edit_profile_page.change_hide_email_state()
        edit_profile_page.click_update_account()

        view_profile_page = home_page.header.click_view_profile()
        final_state = view_profile_page.is_email_field_present

        Assert.not_equal(initial_state, final_state, 'The initial and final states are the same. The profile change failed.')

    @pytest.mark.native
    @pytest.mark.login
    def test_user_can_update_profile_information_in_account_settings_page(self, mozwebqa):
        home_page = Home(mozwebqa)
        home_page.login(user="user.edit")

        Assert.true(home_page.is_the_current_page)
        Assert.true(home_page.header.is_user_logged_in)

        user_edit_page = home_page.header.click_edit_profile()
        Assert.true(user_edit_page.is_the_current_page)

        # save initial values to restore them after the test is finished
        fields_no = len(user_edit_page.profile_fields) - 1
        initial_value = [None] * fields_no
        random_name = "test%s" % random.randrange(1, 100)

        # enter new values
        for i in range(0, fields_no):
            initial_value[i] = deepcopy(user_edit_page.profile_fields[i].field_value)
            user_edit_page.profile_fields[i].clear_field()
            user_edit_page.profile_fields[i].type_value(random_name)

        user_edit_page.click_update_account()
        Assert.equal(user_edit_page.update_message, "Profile Updated")

        # using try finally to ensure that the initial values are restore even if the Asserts fail.
        try:
            for i in range(0, fields_no):
                Assert.contains(random_name, user_edit_page.profile_fields[i].field_value)

        except Exception as exception:
            Assert.fail(exception.msg)

        finally:
            # restore initial values
            for i in range(0, fields_no):
                user_edit_page.profile_fields[i].clear_field()
                user_edit_page.profile_fields[i].type_value(initial_value[i])

            user_edit_page.click_update_account()

########NEW FILE########
__FILENAME__ = test_details
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from unittestzero import Assert

from pages.mobile.details import Details


class TestDetails:

    @pytest.mark.nondestructive
    def test_that_contribute_button_is_not_present_on_the_mobile_page(self, mozwebqa):
        details_page = Details(mozwebqa, 'MemChaser')
        Assert.true(details_page.is_the_current_page)
        Assert.false(details_page.is_contribute_button_present)

########NEW FILE########
__FILENAME__ = test_extensions
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from unittestzero import Assert
from pages.mobile.home import Home


class TestExtensions:

    sort_options = ['Featured', 'Most Users', 'Top Rated', 'Newest', 'Name', 'Weekly Downloads', 'Recently Updated', 'Up & Coming']

    @pytest.mark.nondestructive
    def test_sort_by_region(self, mozwebqa):

        home = Home(mozwebqa)
        extensions_page = home.click_all_featured_addons_link()
        sort_menu = extensions_page.click_sort_by()
        Assert.true(sort_menu.is_extensions_dropdown_visible)

        actual_options = sort_menu.options
        expected_options = self.sort_options
        Assert.equal(len(actual_options), len(expected_options))

        for i in range(len(actual_options)):
            Assert.equal(actual_options[i].name, expected_options[i])
            Assert.true(actual_options[i].is_option_visible)

########NEW FILE########
__FILENAME__ = test_home
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from unittestzero import Assert
from pages.mobile.home import Home
from pages.mobile.themes import Themes


class TestHome:

    expected_menu_items = ['MOZILLA FIREFOX', 'FEATURES', 'DESKTOP', 'ADD-ONS', 'SUPPORT', 'VISIT MOZILLA']

    expected_tabs = ['Featured', 'Categories', 'Themes']

    expected_category_items = ['Alerts & Updates', 'Appearance', 'Bookmarks', 'Download Management',
                               'Feeds, News & Blogging', 'Games & Entertainment', 'Language Support',
                               'Photos, Music & Videos', 'Privacy & Security', 'Search Tools', 'Shopping',
                               'Social & Communication', 'Tabs', 'Web Development', 'Other']

    @pytest.mark.nondestructive
    def test_that_checks_the_desktop_version_link(self, mozwebqa):
        home = Home(mozwebqa)
        Assert.true(home.is_the_current_page)

        Assert.equal('VIEW FULL SITE', home.footer.desktop_version_text)

        home_desktop = home.footer.click_desktop_version()
        Assert.true(home_desktop.is_the_current_page)

    @pytest.mark.nondestructive
    def test_that_checks_header_text_and_page_title(self, mozwebqa):
        home = Home(mozwebqa)
        Assert.true(home.is_the_current_page)

        Assert.equal('ADD-ONS', home.header_text)
        Assert.equal('Return to the Firefox Add-ons homepage', home.header_title)
        Assert.equal('Easy ways to personalize.', home.header_statement_text)

    @pytest.mark.nondestructive
    def test_that_checks_learn_more_link(self, mozwebqa):
        home = Home(mozwebqa)
        Assert.true(home.is_the_current_page)

        Assert.equal(u'Learn More\xbb', home.learn_more_text)
        home.click_learn_more()

        Assert.true(home.is_learn_more_msg_visible)
        Assert.equal("Add-ons are applications that let you personalize Firefox with extra functionality and style. Whether you mistype the name of a website or can't read a busy page, there's an add-on to improve your on-the-go browsing.",
                     home.learn_more_msg_text)

    @pytest.mark.nondestructive
    def test_that_checks_the_firefox_logo(self, mozwebqa):

        home = Home(mozwebqa)
        Assert.true(home.is_the_current_page)

        Assert.true(home.is_header_firefox_logo_visible)
        Assert.contains('firefox.png', home.firefox_header_logo_src)

    @pytest.mark.nondestructive
    def test_that_checks_the_footer_items(self, mozwebqa):
        home = Home(mozwebqa)
        Assert.true(home.is_the_current_page)

        Assert.true(home.footer.is_other_language_dropdown_visible)
        Assert.equal('Other languages', home.footer.other_language_text)
        Assert.equal('Privacy Policy', home.footer.privacy_text)
        Assert.equal('Legal Notices', home.footer.legal_text)

    @pytest.mark.nondestructive
    def test_all_featured_extensions_link(self, mozwebqa):

        home = Home(mozwebqa)
        Assert.true(home.is_the_current_page)
        Assert.equal(home.default_selected_tab_text, 'Featured')

        home.scroll_down  # workaround for selenium scroll issue

        featured_extensions = home.click_all_featured_addons_link()

        Assert.equal(featured_extensions.title, 'ADD-ONS')
        Assert.equal(featured_extensions.page_header, 'Featured Extensions')
        Assert.contains('sort=featured', featured_extensions.get_url_current_page())

    @pytest.mark.nondestructive
    def test_that_checks_the_search_box_and_button(self, mozwebqa):
        home = Home(mozwebqa)
        Assert.true(home.is_the_current_page)

        Assert.true(home.is_search_box_visible)
        Assert.equal('search for add-ons', home.search_box_placeholder)
        Assert.true(home.is_search_button_visible)

    @pytest.mark.nondestructive
    def test_expandable_header(self, mozwebqa):
        home = Home(mozwebqa)
        home.header.click_header_menu()
        Assert.true(home.header.is_dropdown_menu_visible)

        menu_names = [menu.name for menu in home.header.dropdown_menu_items]
        Assert.equal(menu_names, self.expected_menu_items)

    def test_that_checks_the_tabs(self, mozwebqa):
        home = Home(mozwebqa)
        Assert.true(home.is_the_current_page)

        Assert.equal(3, len(home.tabs))

        # Ignore the last tab "Themes" because it redirects to another page
        for tab in reversed(range(len(home.tabs[:-1]))):
            Assert.equal(self.expected_tabs[tab], home.tabs[tab].name)
            home.tabs[tab].click()
            Assert.true(home.tabs[tab].is_tab_selected, "The tab '%s' is not selected." % home.tabs[tab].name)
            Assert.true(home.tabs[tab].is_tab_content_visible,
                        "The content of tab '%s' is not visible." % home.tabs[tab].name)

        # Click on the themes tab separately
        home.tabs[-1].click()
        themes = Themes(mozwebqa)
        themes.is_the_current_page

    @pytest.mark.nondestructive
    def test_the_amo_logo_text_and_title(self, mozwebqa):
        home = Home(mozwebqa)
        Assert.true(home.is_the_current_page)

        Assert.equal('Return to the Firefox Add-ons homepage', home.logo_title)
        Assert.equal('ADD-ONS', home.logo_text)
        Assert.contains('/media/img/zamboni/app_icons/firefox.png', home.logo_image_src)
        Assert.equal('Easy ways to personalize.', home.subtitle)

    @pytest.mark.nondestructive
    def test_category_items(self, mozwebqa):
        home = Home(mozwebqa)
        home.tab('Categories').click()
        Assert.true(home.is_categories_region_visible)

        for i in range(len(home.categories)):
            Assert.equal(home.categories[i].name, self.expected_category_items[i])

########NEW FILE########
__FILENAME__ = test_search
#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from unittestzero import Assert

from pages.mobile.home import Home


class TestSearch:

    positive_search_term = "firefox"

    @pytest.mark.nondestructive
    def test_that_search_returns_results(self, mozwebqa):
        home = Home(mozwebqa)

        search_page = home.search_for(self.positive_search_term)

        Assert.greater(len(search_page.results), 0)

########NEW FILE########
