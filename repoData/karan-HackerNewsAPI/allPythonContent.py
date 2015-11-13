__FILENAME__ = constants
#!/usr/bin/env python

BASE_URL = 'https://news.ycombinator.com'
INTERVAL_BETWEEN_REQUESTS = 1 # seconds to sleep between 2 consecutive page requests
########NEW FILE########
__FILENAME__ = hn
#!/usr/bin/env python

"""
Hacker News API
Unofficial Python API for Hacker News.

@author Karan Goel
@email karan@goel.im
"""


import re
import time

from .utils import get_soup, get_item_soup
from .constants import BASE_URL, INTERVAL_BETWEEN_REQUESTS


class HN(object):
    """
    The class that parses the HN page, and builds up all stories
    """

    def __init__(self):
        self.more = ''

    # def _get_next_page(self, soup):
    #     """
    #     Get the relative url of the next page (The "More" link at
    #     the bottom of the page)
    #     """
    #     table = soup.findChildren('table')[2] # the table with all submissions
    #     # the last row of the table contains the relative url of the next page
    #     return table.findChildren(['tr'])[-1].find('a').get('href').replace(BASE_URL, '').lstrip('//')

    def _get_zipped_rows(self, soup):
        """
        Returns all 'tr' tag rows as a list of tuples. Each tuple is for
        a single story.
        """
        table = soup.findChildren('table')[2] # the table with all submissions
        rows = table.findChildren(['tr'])[:-2] # get all rows but last 2
        # remove the spacing rows
        spacing = range(2, len(rows), 3) # indices of spacing tr's
        rows = [row for (i, row) in enumerate(rows) if (i not in spacing)]
        # rank, title, domain
        info = [row for (i, row) in enumerate(rows) if (i % 2 == 0)]
        # points, submitter, comments
        detail = [row for (i, row) in enumerate(rows) if (i % 2 != 0)]

        return zip(info, detail) # build a list of tuple for all post

    def _build_story(self, all_rows):
        """
        Builds and returns a list of stories (dicts) from the passed source.
        """
        all_stories = [] # list to hold all stories

        for (info, detail) in all_rows:

            #-- Get the into about a story --#
            info_cells = info.findAll('td') # split in 3 cells

            rank = int(info_cells[0].string[:-1])
            title = '%s' % info_cells[2].find('a').string
            link = info_cells[2].find('a').get('href')

            is_self = False # by default all stories are linking posts

            if link.find('item?id=') is -1: # the link doesn't contains "http" meaning an internal link
                domain = info_cells[2].find('span').string[2:-2] # slice " (abc.com) "
            else:
                link = '%s/%s' % (BASE_URL, link)
                domain = BASE_URL
                is_self = True
            #-- Get the into about a story --#

            #-- Get the detail about a story --#
            detail_cell = detail.findAll('td')[1] # split in 2 cells, we need only second
            detail_concern = detail_cell.contents # list of details we need, 5 count

            num_comments = -1

            if re.match(r'^(\d+)\spoint.*', detail_concern[0].string) is not None:
                # can be a link or self post
                points = int(re.match(r'^(\d+)\spoint.*', detail_concern[0].string).groups()[0])
                submitter = '%s' % detail_concern[2].string
                submitter_profile = '%s/%s' % (BASE_URL, detail_concern[2].get('href'))
                published_time = ' '.join(detail_concern[3].strip().split()[:3])
                comment_tag = detail_concern[4]
                story_id = int(re.match(r'.*=(\d+)', comment_tag.get('href')).groups()[0])
                comments_link = '%s/item?id=%d' % (BASE_URL, story_id)
                comment_count = re.match(r'(\d+)\s.*', comment_tag.string)
                try:
                    # regex matched, cast to int
                    num_comments = int(comment_count.groups()[0])
                except AttributeError:
                    # did not match, assign 0
                    num_comments = 0
            else: # this is a job post
                points = 0
                submitter = ''
                submitter_profile = ''
                published_time = '%s' % detail_concern[0]
                comment_tag = ''
                try:
                    story_id = int(re.match(r'.*=(\d+)', link).groups()[0])
                except AttributeError:
                    story_id = -1 # job listing that points to external link
                comments_link = ''
                comment_count = -1
            #-- Get the detail about a story --#

            story = Story(rank, story_id, title, link, domain, points, submitter,
                 published_time, submitter_profile, num_comments, comments_link,
                 is_self)

            all_stories.append(story)

        return all_stories


    def get_stories(self, story_type='', limit=30):
        """
        Yields a list of stories from the passed page
        of HN.
        'story_type' can be:
        \t'' = top stories (homepage) (default)
        \t'news2' = page 2 of top stories
        \t'newest' = most recent stories
        \t'best' = best stories

        'limit' is the number of stories required from the given page.
        Defaults to 30. Cannot be more than 30.
        """
        if limit == None or limit < 1 or limit > 30:
            limit = 30 # we need at least 30 items

        stories_found = 0
        # self.more = story_type
        # while we still have more stories to find
        while stories_found < limit:
            soup = get_soup(page=story_type) # get current page soup
            all_rows = self._get_zipped_rows(soup)
            stories = self._build_story(all_rows) # get a list of stories on current page
            # self.more = self._get_next_page(soup) # move to next page

            for story in stories:
                yield story
                stories_found += 1

                # if enough stories found, return
                if stories_found == limit:
                    return

    def get_leaders(self, limit=10):
        """ Return the leaders of Hacker News """
        if limit == None:
            limit = 10
        soup = get_soup('leaders')
        table = soup.find('table')
        leaders_table = table.find_all('table')[1]
        listLeaders = leaders_table.find_all('tr')[2:]
        listLeaders.pop(10) # Removing because empty in the Leaders page
        for i, leader in enumerate(listLeaders):
            if (i == limit): 
                return
            if not leader.text == '':
                item = leader.find_all('td')
                yield User(item[1].text,'', item[2].text, item[3].text)

class Story(object):
    """
    Story class represents one single story on HN
    """

    def __init__(self, rank, story_id, title, link, domain, points, submitter,
                published_time, submitter_profile, num_comments, comments_link,
               is_self):
        self.rank = rank # the rank of story on the page
        self.story_id = story_id # the story's id
        self.title = title # the title of the story
        self.link = link # the url it points to (None for self posts)
        self.domain = domain # the domain of the link (None for self posts)
        self.points = points # the points/karma on the story
        self.submitter = submitter # the user who submitted the story
        self.published_time = published_time # publish time of story
        self.submitter_profile = submitter_profile # link to submitter's profile
        self.num_comments = num_comments # the number of comments it has
        self.comments_link = comments_link # the link to the comments page
        self.is_self = is_self # Truw is a self post

    def __repr__(self):
        """
        A string representation of the class object
        """
        return '<Story: ID={0}>'.format(self.story_id)

    def _get_next_page(self, soup, current_page):
        """
        Get the relative url of the next page (The "More" link at
        the bottom of the page)
        """

        # Get the table with all the comments:
        if current_page == 1:
            table = soup.findChildren('table')[3]
        elif current_page > 1:
            table = soup.findChildren('table')[2]

        # the last row of the table contains the relative url of the next page
        anchor = table.findChildren(['tr'])[-1].find('a')
        if anchor and anchor.text == u'More':
            return anchor.get('href').lstrip(BASE_URL)
        else:
            return None

    def _build_comments(self, soup):
        """
        For the story, builds and returns a list of Comment objects.
        """

        comments = []
        current_page = 1

        while True:
            # Get the table holding all comments:
            if current_page == 1:
                table = soup.findChildren('table')[3]
            elif current_page > 1:
                table = soup.findChildren('table')[2]

            rows = table.findChildren(['tr']) # get all rows (each comment is duplicated twice)
            rows = rows[:len(rows) - 2] # last row is more, second last is spacing
            rows = [row for i, row in enumerate(rows) if (i % 2 == 0)] # now we have unique comments only

            if len(rows) > 1:
                for row in rows:

                    # skip an empty td
                    if not row.findChildren('td'):
                        continue

                    ## Builds a flat list of comments

                    # level of comment, starting with 0
                    level = int(row.findChildren('td')[1].find('img').get('width')) // 40

                    spans = row.findChildren('td')[3].findAll('span')
                    # span[0] = submitter details
                    # [<a href="user?id=jonknee">jonknee</a>, u' 1 hour ago  | ', <a href="item?id=6910978">link</a>]
                    # span[1] = actual comment

                    if str(spans[0]) != '<span class="comhead"></span>':
                        user = spans[0].contents[0].string # user who submitted the comment
                        time_ago = spans[0].contents[1].string.strip().rstrip(' |') # relative time of comment
                        try:
                            comment_id = int(re.match(r'item\?id=(.*)', spans[0].contents[2].get('href')).groups()[0])
                        except AttributeError:
                            comment_id = int(re.match(r'%s/item\?id=(.*)' % BASE_URL, spans[0].contents[2].get('href')).groups()[0])

                        body = spans[1].text # text representation of comment (unformatted)
                        
                        if body[-2:] == '--':
                            body = body[:-5]

                        # html of comment, may not be valid
                        try:
                            pat = re.compile(r'<span class="comment"><font color=".*">(.*)</font></span>')
                            body_html = re.match(pat, str(spans[1]).replace('\n', '')).groups()[0]
                        except AttributeError:
                            pat = re.compile(r'<span class="comment"><font color=".*">(.*)</font></p><p><font size="1">')
                            body_html = re.match(pat, str(spans[1]).replace('\n', '')).groups()[0]

                    else:
                        # comment deleted
                        user = ''
                        time_ago = ''
                        comment_id = -1
                        body = '[deleted]'
                        body_html = '[deleted]'

                    comment = Comment(comment_id, level, user, time_ago, body, body_html)
                    comments.append(comment)

            # Move on to the next page of comments, or exit the loop if there
            # is no next page.
            next_page_url = self._get_next_page(soup, current_page)
            if not next_page_url:
                break

            soup = get_soup(page=next_page_url)
            current_page += 1

        # previous_comment = None
        # for comment in comments:
        #     if comment.level == 0:
        #         previous_comment = comment
        #     else:
        #         level_difference = comment.level - previous_comment.level
        #         previous_comment.body_html += '\n' + '\t' * level_difference + comment.body_html
        #         previous_comment.body += '\n' + '\t' * level_difference + comment.body         
        return comments
    
    @classmethod
    def fromid(self, item_id):
        """
        Initializes an instance of Story for given item_id.
        It is assumed that the story referenced by item_id is valid
        and does not raise any HTTP errors.
        item_id is an int.
        """
        if not item_id:
            raise Exception('Need an item_id for a story')
        # get details about a particular story
        soup = get_item_soup(item_id)
        
        # this post has not been scraped, so we explititly get all info
        story_id = item_id
        rank = -1
        
        info_table = soup.findChildren('table')[2] # to extract meta information about the post
        info_rows = info_table.findChildren('tr') # [0] = title, domain, [1] = points, user, time, comments
        
        title_row = info_rows[0].findChildren('td')[1] # title, domain
        title = title_row.find('a').text
        try:
            domain = title_row.find('span').string[2:-2]
            # domain found
            is_self = False
            link = title_row.find('a').get('href')
        except AttributeError:
            # self post
            domain = BASE_URL
            is_self = True
            link = '%s/item?id=%s' % (BASE_URL, item_id)
        
        meta_row = info_rows[1].findChildren('td')[1].contents # points, user, time, comments
        # [<span id="score_7024626">789 points</span>, u' by ', <a href="user?id=endianswap">endianswap</a>,
        # u' 8 hours ago  | ', <a href="item?id=7024626">238 comments</a>]

        points = int(re.match(r'^(\d+)\spoint.*', meta_row[0].text).groups()[0])
        submitter = meta_row[2].text
        submitter_profile = '%s/%s' % (BASE_URL, meta_row[2].get('href'))
        published_time = ' '.join(meta_row[3].strip().split()[:3])
        comments_link = '%s/item?id=%s' % (BASE_URL, item_id)
        try:
            num_comments = int(re.match(r'(\d+)\s.*', meta_row[4].text).groups()[0])
        except AttributeError:
            num_comments = 0
        story = Story(rank, story_id, title, link, domain, points, submitter,
                published_time, submitter_profile, num_comments, comments_link,
               is_self)
        return story

    def get_comments(self):
        """
        Returns a list of Comment(s) for the given story
        """
        soup = get_item_soup(self.story_id)
        return self._build_comments(soup)


class Comment(object):
    """
    Represents a comment on a post on HN
    """

    def __init__(self, comment_id, level, user, time_ago, body, body_html):
        self.comment_id = comment_id # the comment's item id
        self.level = level # commen's nesting level
        self.user = user # user's name who submitted the post
        self.time_ago = time_ago # time when it was submitted
        self.body = body # text representation of comment (unformatted)
        self.body_html = body_html # html of comment, may not be valid

    def __repr__(self):
        """
        A string representation of the class object
        """
        return '<Comment: ID={0}>'.format(self.comment_id)

class User(object):
    """
    Represents a User on HN
    """

    def __init__(self, username, date_created,karma, avg):
        self.username = username
        self.date_created = date_created
        self.karma = karma
        self.avg = avg

    def __repr__(self):
        return '{0} {1} {2}'.format(self.username, self.karma, self.avg)


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python

import requests
from bs4 import BeautifulSoup

from .constants import BASE_URL, INTERVAL_BETWEEN_REQUESTS

def get_soup(page=''):
    """
    Returns a bs4 object of the page requested
    """
    content = requests.get('%s/%s' % (BASE_URL, page)).text
    return BeautifulSoup(content)

def get_item_soup(story_id):
    """
    Returns a bs4 object of the requested story
    """
    return get_soup(page='item?id=' + str(story_id))

########NEW FILE########
__FILENAME__ = my_test_bot
#!/usr/bin/env python

from hn import HN, Story

hn = HN()

top_iter = hn.get_stories(limit=30) # a generator over 30 stories from top page


# print top stories from homepage
for story in top_iter:
    print(story.title)
    #print('[{0}] "{1}" by {2}'.format(story.points, story.title, story.submitter))


# print 10 latest stories
for story in hn.get_stories(story_type='newest', limit=10):
    story.title
    print('*' * 50)
    print('')


# for each story on front page, print top comment
for story in hn.get_stories():
    print(story.title)
    comments = story.get_comments()
    print(comments[0] if len(comments) > 0 else None)
    print('*' * 10)



# print top 5 comments with nesting for top 5 stories
for story in hn.get_stories(story_type='best', limit=5):
    print(story.title)
    comments = story.get_comments()
    if len(comments) > 0:
        for comment in comments[:5]:
            print('\t' * (comment.level + 1) + comment.body[:min(30, len(comment.body))])
    print('*' * 10)

# get the comments from any custom story
story = Story.fromid(6374031)
comments = story.get_comments()

########NEW FILE########
__FILENAME__ = test_leaders
import unittest

from hn import HN, Story
from hn import utils, constants

from test_utils import get_content, PRESETS_DIR

import httpretty

class TestGetLeaders(unittest.TestCase):

	def setUp(self):
		# check py version
		#self.PY2 = sys.version_info[0] == 2
		self.hn = HN()
		httpretty.HTTPretty.enable()
		httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'leaders'),
                           body=get_content('leaders.html'))

	def tearDown(self):
		httpretty.HTTPretty.disable()

	def test_get_leaders_with_no_parameter(self):
		result = [leader for leader in self.hn.get_leaders()]
		self.assertEqual(len(result), 10)

	def test_get_leaders_with_parameter(self):
		value = 50
		result = [leader for leader in self.hn.get_leaders(value)]
		self.assertEqual(len(result), value)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pagination
import unittest
from os import path
import sys

# from hn import HN, Story
# from hn import utils, constants

# from test_utils import get_content, PRESETS_DIR

# import httpretty

# class TestPagination(unittest.TestCase):

#     def setUp(self):
#         httpretty.HTTPretty.enable()
#         httpretty.register_uri(httpretty.GET, 'https://news.ycombinator.com/', 
#             body=get_content('index.html'))
#         httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'best'), 
#             body=get_content('best.html'))
#         httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'newest'), 
#             body=get_content('newest.html'))
#         httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'x?fnid=WK2fLO5cPAJ9DnZbm8XOFR'), 
#             body=get_content('best2.html'))
#         httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'news2'), 
#             body=get_content('news2.html'))

#         # check py version
#         self.PY2 = sys.version_info[0] == 2
#         self.hn = HN()

#     def tearDown(self):
#         httpretty.HTTPretty.disable()
    
#     # def test_more_link_top(self):
#     #     """
#     #     Checks if the "More" link at the bottom of homepage works.
#     #     """
#     #     soup = utils.get_soup()
#     #     fnid = self.hn._get_next_page(soup)[-5:]
#     #     expected = 'news2'
#     #     self.assertEqual(len(fnid), len(expected))
        
#     # def test_more_link_best(self):
#     #     """
#     #     Checks if the "More" link at the bottom of best page works.
#     #     """
#     #     soup = utils.get_soup(page='best')
#     #     fnid = self.hn._get_next_page(soup)[-29:]
#     #     expected = 'x?fnid=te9bsVN2BAx0XOpRmUjcY4'
#     #     self.assertEqual(len(fnid), len(expected))
        
#     # def test_more_link_newest(self):
#     #     """
#     #     Checks if the "More" link at the bottom of newest page works.
#     #     """
#     #     soup = utils.get_soup(page='newest')
#     #     fnid = self.hn._get_next_page(soup)[-29:]
#     #     expected = 'x?fnid=te9bsVN2BAx0XOpRmUjcY4'
#     #     self.assertEqual(len(fnid), len(expected))
    
#     def test_get_zipped_rows(self):
#         """
#         Tests HN._get_zipped_rows for best page.
#         """
#         soup = utils.get_soup(page='best')
#         rows = self.hn._get_zipped_rows(soup)
#         if self.PY2:
#             self.assertEqual(len(rows), 30)
#         else:
#             rows = [row for row in rows]
#             self.assertEqual(len(rows), 30)
    
#     def test_pagination_top_for_0_limit(self):
#         """
#         Checks if the pagination works for 0 limit.
#         """
#         stories = [story for story in self.hn.get_stories(limit=0)]
#         self.assertEqual(len(stories), 30)
    
#     def test_pagination_top_for_2_pages(self):
#         """
#         Checks if the pagination works for the front page.
#         """
#         stories = [story for story in self.hn.get_stories(limit=2*30)]
#         self.assertEqual(len(stories), 2 * 30)
    
#     def test_pagination_newest_for_3_pages(self):
#         """
#         Checks if the pagination works for the newest page.
#         """
#         stories = [story for story in self.hn.get_stories(story_type='newest', limit=3*30)]
#         self.assertEqual(len(stories), 3 * 30)
        
#     def test_pagination_best_for_2_pages(self):
#         """
#         Checks if the pagination works for the best page.
#         """
#         stories = [story for story in self.hn.get_stories(story_type='best', limit=2*30)]
#         self.assertEqual(len(stories), 2 * 30)


# if __name__ == '__main__':
#     unittest.main()

########NEW FILE########
__FILENAME__ = test_stories_dict_structure
import unittest
from os import path
import sys

from hn import HN, Story
from hn import utils, constants

from test_utils import get_content, PRESETS_DIR

import httpretty

class TestStoriesDict(unittest.TestCase):
    
    def setUp(self):
        httpretty.HTTPretty.enable()
        httpretty.register_uri(httpretty.GET, 'https://news.ycombinator.com/', 
            body=get_content('index.html'))
        httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'best'), 
            body=get_content('best.html'))
        httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'newest'), 
            body=get_content('newest.html'))

        # check py version
        PY2 = sys.version_info[0] == 2
        if not PY2:
            self.text_type = [str]
        else:
            self.text_type = [unicode, str]

        self.hn = HN()
        self.top_stories = [story for story in self.hn.get_stories()]
        self.newest_stories = [story for story in self.hn.get_stories(story_type='newest')]
        self.best_stories = [story for story in self.hn.get_stories(story_type='best')]
    
    def tearDown(self):
        httpretty.HTTPretty.disable()
    
    
    def test_stories_dict_structure_top(self):
        """
        Checks data type of each field of each story from front page.
        """
        for story in self.top_stories:
            # testing for unicode or string
            # because the types are mixed sometimes
            assert type(story.rank) == int
            assert type(story.story_id) == int
            assert type(story.title) in self.text_type
            assert type(story.link) in self.text_type
            assert type(story.domain) in self.text_type
            assert type(story.points) == int
            assert type(story.submitter) in self.text_type
            assert type(story.published_time) in self.text_type
            assert type(story.submitter_profile) in self.text_type
            assert type(story.num_comments) == int
            assert type(story.comments_link) in self.text_type
            assert type(story.is_self) == bool
    
    def test_stories_dict_structure_newest(self):
        """
        Checks data type of each field of each story from newest page
        """
        for story in self.newest_stories:
            # testing for unicode or string
            # because the types are mixed sometimes
            assert type(story.rank) == int
            assert type(story.story_id) == int
            assert type(story.title) in self.text_type
            assert type(story.link) in self.text_type
            assert type(story.domain) in self.text_type
            assert type(story.points) == int
            assert type(story.submitter) in self.text_type
            assert type(story.published_time) in self.text_type
            assert type(story.submitter_profile) in self.text_type
            assert type(story.num_comments) == int
            assert type(story.comments_link) in self.text_type
            assert type(story.is_self) == bool
    
    def test_stories_dict_structure_best(self):
        """
        Checks data type of each field of each story from best page
        """
        for story in self.best_stories:
            # testing for unicode or string
            # because the types are mixed sometimes
            assert type(story.rank) == int
            assert type(story.story_id) == int
            assert type(story.title) in self.text_type
            assert type(story.link) in self.text_type
            assert type(story.domain) in self.text_type
            assert type(story.points) == int
            assert type(story.submitter) in self.text_type
            assert type(story.published_time) in self.text_type
            assert type(story.submitter_profile) in self.text_type
            assert type(story.num_comments) == int
            assert type(story.comments_link) in self.text_type
            assert type(story.is_self) == bool
    
    def test_stories_dict_length_top(self):
        """
        Checks if the dict returned by scraping the front page of HN is 30.
        """
        self.assertEqual(len(self.top_stories), 30)
    
    def test_stories_dict_length_best(self):
        """
        Checks if the dict returned by scraping the best page of HN is 30.
        """
        self.assertEqual(len(self.best_stories), 30)
        
    def test_stories_dict_length_top_newest(self):
        """
        Checks if the dict returned by scraping the newest page of HN is 30.
        """
        self.assertEqual(len(self.newest_stories), 30)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_story_class
import unittest
from os import path
import sys

from hn import HN, Story
from hn import utils, constants

from test_utils import get_content, PRESETS_DIR

import httpretty

class TestStory(unittest.TestCase):
    
    def setUp(self):
        httpretty.HTTPretty.enable()
        httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'item?id=6115341'), 
            body=get_content('6115341.html'))

        self.PY2 = sys.version_info[0] == 2
        if not self.PY2:
            self.text_type = [str]
        else:
            self.text_type = [unicode, str]
        # https://news.ycombinator.com/item?id=6115341
        self.story = Story.fromid(6115341)
    
    def tearDown(self):
        httpretty.HTTPretty.disable()
    
    def test_story_data_types(self):
        """
        Test types of fields of a Story object
        """
        assert type(self.story.rank) == int
        assert type(self.story.story_id) == int
        assert type(self.story.title) in self.text_type
        assert type(self.story.link) in self.text_type
        assert type(self.story.domain) in self.text_type
        assert type(self.story.points) == int
        assert type(self.story.submitter) in self.text_type
        assert type(self.story.published_time) in self.text_type
        assert type(self.story.submitter_profile) in self.text_type
        assert type(self.story.num_comments) == int
        assert type(self.story.comments_link) in self.text_type
        assert type(self.story.is_self) == bool
    
    def test_story_submitter(self):
        """
        Tests the author name
        """
        self.assertEqual(self.story.submitter, 'karangoeluw')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_story_fromid
import unittest
from os import path
import sys

from hn import HN, Story
from hn import utils, constants

from test_utils import get_content, PRESETS_DIR

import httpretty

class TestStoryFromId(unittest.TestCase):

    def setUp(self):
        httpretty.HTTPretty.enable()
        httpretty.register_uri(httpretty.GET, 'https://news.ycombinator.com/', 
            body=get_content('index.html'))
        httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'item?id=6115341'), 
            body=get_content('6115341.html'))

        # check py version
        self.PY2 = sys.version_info[0] == 2
        self.hn = HN()
        self.story = Story.fromid(6115341)

    def tearDown(self):
        httpretty.HTTPretty.disable()

    def test_from_id_constructor(self):
        """
        Tests whether or not the constructor fromid works or not
        by testing the returned Story.
        """
        self.assertEqual(self.story.submitter, 'karangoeluw')
        self.assertEqual(self.story.title, 'Github: What does the "Gold Star" next to my repository (in Explore page) mean?')
        self.assertTrue(self.story.is_self)

    def test_comment_for_fromid(self):
        """
        Tests if the comment scraping works for fromid or not.
        """
        comments = self.story.get_comments()
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].comment_id, 6115436)
        self.assertEqual(comments[2].level, 2)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_story_get_comments
import unittest
from os import path
import sys
from random import randrange

from hn import HN, Story
from hn import utils, constants

from test_utils import get_content, PRESETS_DIR

import httpretty

class TestStoryGetComments(unittest.TestCase):

    def setUp(self):
        httpretty.HTTPretty.enable()
        httpretty.register_uri(httpretty.GET, 'https://news.ycombinator.com/', 
            body=get_content('index.html'))
        httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'item?id=7324236'), 
            body=get_content('7324236.html'))
        httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'x?fnid=0MonpGsCkcGbA7rcbd2BAP'), 
            body=get_content('7324236-2.html'))
        httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'x?fnid=jyhCSQtM6ymFazFplS4Gpf'), 
            body=get_content('7324236-3.html'))
        httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'x?fnid=s3NA4qB6zMT3KHVk1x2MTG'), 
            body=get_content('7324236-4.html'))
        httpretty.register_uri(httpretty.GET, '%s/%s' % (constants.BASE_URL, 'x?fnid=pFxm5XBkeLtmphVejNZWlo'), 
            body=get_content('7324236-5.html'))

        story = Story.fromid(7324236)
        self.comments = story.get_comments()

    def tearDown(self):
        httpretty.HTTPretty.disable()

    def test_get_comments_len(self):
        """
        Tests whether or not len(get_comments) > 90 if there are multiple pages
        of comments.
        """
        # Note: Hacker News is not consistent about the number of comments per
        # page. On multiple comment page stories, the number of comments on a
        # page is never less than 90. On single comment page stories, the
        # number of comments on the sole page is always less than 110.
        self.assertTrue(len(self.comments) > 90)

    def test_comment_not_null(self):
        """
        Tests for null comments.
        """
        comment = self.comments[randrange(0, len(self.comments))]
        self.assertTrue(bool(comment.body))
        self.assertTrue(bool(comment.body_html))

    def test_get_nested_comments(self):
        comment = self.comments[0].body
        self.assertEqual(comment.index("Healthcare.gov"), 0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utils
from os import path

PRESETS_DIR = path.join(path.dirname(__file__), 'presets')

def get_content(file):
    with open(path.join(PRESETS_DIR, file)) as f:
        return f.read()

########NEW FILE########
