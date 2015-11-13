__FILENAME__ = test_checkins
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import BaseAuthenticatedEndpointTestCase



class CheckinsEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_checkin(self):
        response = self.api.checkins.add(params={'venueId': self.default_venueid})
        assert 'checkin' in response

    def test_recent(self):
        response = self.api.checkins.recent()
        assert 'recent' in response

    def test_recent_location(self):
        response = self.api.checkins.recent(params={'ll': self.default_geo})
        assert 'recent' in response

    def test_recent_limit(self):
        response = self.api.checkins.recent(params={'limit': 10})
        assert 'recent' in response

########NEW FILE########
__FILENAME__ = test_events
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import BaseAuthenticatedEndpointTestCase, BaseUserlessEndpointTestCase



class EventsEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_event(self):
        response = self.api.events(self.default_eventid)
        assert 'event' in response


    def test_categories(self):
        response = self.api.events.categories()
        assert 'categories' in response


    def test_search(self):
        response = self.api.events.search(params={'domain': u'songkick.com', 'eventId': u'8183976'})
        assert 'events' in response



class EventsUserlessEndpointTestCase(BaseUserlessEndpointTestCase):
    """
    General
    """
    def test_categories(self):
        response = self.api.events.categories()
        assert 'categories' in response


    def test_search(self):
        response = self.api.events.search(params={'domain': u'songkick.com', 'eventId': u'8183976'})
        assert 'events' in response

########NEW FILE########
__FILENAME__ = test_lang
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import MultilangEndpointTestCase



class MultiLangTestCase(MultilangEndpointTestCase):
    """
    General
    """
    def test_lang(self):
        """Test a wide swath of languages"""
        for api in self.apis:
            categories = api.venues.categories()
            assert 'categories' in categories, u"'categories' not in response"
            assert len(categories['categories']) > 1, u'Expected multiple categories'

########NEW FILE########
__FILENAME__ = test_lists
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import BaseAuthenticatedEndpointTestCase, BaseUserlessEndpointTestCase



class ListsEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_list(self):
        response = self.api.lists(self.default_listid)
        assert 'list' in response



class ListsUserlessEndpointTestCase(BaseUserlessEndpointTestCase):
    """
    General
    """
    def test_list(self):
        response = self.api.lists(self.default_listid)
        assert 'list' in response

########NEW FILE########
__FILENAME__ = test_multi
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

import itertools

from . import BaseAuthenticatedEndpointTestCase



class MultiEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_multi(self):
        """Load up a bunch of multi sub-requests and make sure they process as expected"""
        self.api.users(multi=True)
        self.api.users.leaderboard(params={'neighbors': 5}, multi=True)
        # Throw a non-multi in the middle to make sure we don't create conflicts
        user_response = self.api.users()
        assert 'user' in user_response
        # Resume loading the multi sub-requests
        self.api.users.badges(multi=True)
        # Throw a call with multiple params in the middle to make sure it gets encoded correctly
        # and won't affect the other api calls that share the same http request
        self.api.pages.venues('1070527', params={'limit': 10, 'offset': 10}, multi=True)
        self.api.users.lists(params={'group': u'friends'}, multi=True)
        self.api.venues.categories(multi=True)
        self.api.checkins.recent(params={'limit': 10}, multi=True)
        self.api.tips(self.default_tipid, multi=True)
        self.api.lists(self.default_listid, multi=True)
        self.api.photos(self.default_photoid, multi=True)
        # We are expecting certain responses...
        expected_responses = ('user', 'leaderboard', 'badges', 'venues', 'lists', 'categories', 'recent', 'tip', 'list', 'photo',)
        # Make sure our utility functions are working
        assert len(self.api.multi) == len(expected_responses), u'{0} requests queued. Expecting {1}'.format(
            len(self.api.multi),
            len(expected_responses)
        )
        assert self.api.multi.num_required_api_calls == 2, u'{0} required API calls. Expecting 2'.format(
            self.api.multi.num_required_api_calls
        )
        # Now make sure the multi call comes back with what we want
        for response, expected_response in itertools.izip(self.api.multi(), expected_responses):
            assert expected_response in response, '{0} not in response'.format(expected_response)

########NEW FILE########
__FILENAME__ = test_oauth
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import BaseAuthenticationTestCase



class OAuthEndpointTestCase(BaseAuthenticationTestCase):
    def test_auth_url(self):
        url = self.api.oauth.auth_url()
        assert isinstance(url, basestring)

    def test_get_token(self):
        # Honestly, not much we can do to test here
        pass

########NEW FILE########
__FILENAME__ = test_pages
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import BaseAuthenticatedEndpointTestCase, BaseUserlessEndpointTestCase



class VenuesEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_pages(self):
        response = self.api.pages(self.default_userid)
        assert 'user' in response


    def test_search(self):
        response = self.api.pages.search(params={'name': 'Starbucks'})
        assert 'results' in response


    def test_venues(self):
        response = self.api.pages.venues(self.default_pageid)
        assert 'venues' in response



class VenuesUserlessEndpointTestCase(BaseUserlessEndpointTestCase):
    """
    General
    """
    def test_pages(self):
        response = self.api.pages(self.default_userid)
        assert 'user' in response


    def test_venues(self):
        response = self.api.pages.venues(self.default_pageid)
        assert 'venues' in response

########NEW FILE########
__FILENAME__ = test_photos
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import TEST_DATA_DIR, BaseAuthenticatedEndpointTestCase, BaseUserlessEndpointTestCase

import os



class PhotosEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_photo(self):
        response = self.api.photos(self.default_photoid)
        assert 'photo' in response

    def test_attach_photo(self):
        """Creates a checkin and attaches a photo to it."""
        response = self.api.checkins.add(params={'venueId': self.default_venueid})
        checkin = response.get('checkin')
        self.assertNotEqual(checkin, None)

        test_photo = os.path.join(TEST_DATA_DIR, 'test-photo.jpg')
        # Fail gracefully if we don't have a test photo on disk
        if os.path.isfile(test_photo):
            photo_data = open(test_photo, 'rb')
            try:
                response = self.api.photos.add(params={'checkinId': checkin['id']}, photo_data=photo_data)
                assert 'photo' in response
                photo = response.get('photo')
                self.assertNotEqual(photo, None)
                self.assertEquals(300, photo['width'])
                self.assertEquals(300, photo['height'])
            finally:
                photo_data.close()
        else:
            print u"Put a 'test-photo.jpg' file in the testdata/ directory to enable this test."

########NEW FILE########
__FILENAME__ = test_ratelimit
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import BaseAuthenticatedEndpointTestCase, BaseUserlessEndpointTestCase



class RateLimitTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_rate_limit(self):
        # A call is needed to load the value
        self.api.venues(self.default_venueid)
        assert self.api.rate_limit > 0

    def test_rate_remaining(self):
        # A call is needed to load the value
        self.api.venues(self.default_venueid)
        assert self.api.rate_remaining > 0

########NEW FILE########
__FILENAME__ = test_settings
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import BaseAuthenticatedEndpointTestCase



class SettingsEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_setting(self):
        response = self.api.settings(self.default_settingid)
        assert 'value' in response

    def test_all(self):
        response = self.api.settings.all()
        assert 'settings' in response

########NEW FILE########
__FILENAME__ = test_specials
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import BaseAuthenticatedEndpointTestCase, BaseUserlessEndpointTestCase



class SpecialsEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_special(self):
        response = self.api.specials(self.default_specialid, params={'venueId': self.default_special_venueid})
        assert 'special' in response

    def test_search(self):
        response = self.api.specials.search(params={'ll': self.default_geo})
        assert 'specials' in response

    def test_search_limit(self):
        response = self.api.specials.search(params={'ll': self.default_geo, 'limit': 10})
        assert 'specials' in response



class SpecialsUserlessEndpointTestCase(BaseUserlessEndpointTestCase):
    """
    General
    """
    def test_special(self):
        response = self.api.specials(self.default_specialid, params={'venueId': self.default_special_venueid})
        assert 'special' in response

    def test_search(self):
        response = self.api.specials.search(params={'ll': self.default_geo})
        assert 'specials' in response

    def test_search_limit(self):
        response = self.api.specials.search(params={'ll': self.default_geo, 'limit': 10})
        assert 'specials' in response

########NEW FILE########
__FILENAME__ = test_tips
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import BaseAuthenticatedEndpointTestCase, BaseUserlessEndpointTestCase



class TipsEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_tip(self):
        response = self.api.tips(self.default_tipid)
        assert 'tip' in response


    def test_search(self):
        response = self.api.tips.search({'ll': self.default_geo})
        assert 'tips' in response

    def test_search_limit(self):
        response = self.api.tips.search({'ll': self.default_geo, 'limit': 10})
        assert 'tips' in response

    def test_search_offset(self):
        response = self.api.tips.search({'ll': self.default_geo, 'offset': 3})
        assert 'tips' in response

    def test_search_filter(self):
        response = self.api.tips.search({'ll': self.default_geo, 'filter': 'friends'})
        assert 'tips' in response

    def test_search_query(self):
        response = self.api.tips.search({'ll': self.default_geo, 'query': 'donuts'})
        assert 'tips' in response


    """
    Aspects
    """
    def test_done(self):
        response = self.api.tips.done(self.default_tipid)
        assert 'done' in response

    def test_done_limit(self):
        response = self.api.tips.done(self.default_tipid, {'limit': 10})
        assert 'done' in response

    def test_done_offset(self):
        response = self.api.tips.done(self.default_tipid, {'offset': 3})
        assert 'done' in response


    def test_listed(self):
        response = self.api.tips.listed(self.default_tipid)
        assert 'lists' in response

    def test_listed_group(self):
        response = self.api.tips.listed(self.default_tipid, {'group': 'friends'})
        assert 'lists' in response



class TipsUserlessEndpointTestCase(BaseUserlessEndpointTestCase):
    """
    General
    """
    def test_tip(self):
        response = self.api.tips(self.default_tipid)
        assert 'tip' in response


    def test_search(self):
        response = self.api.tips.search(params={'ll': self.default_geo})
        assert 'tips' in response

    def test_search_limit(self):
        response = self.api.tips.search(params={'ll': self.default_geo, 'limit': 10})
        assert 'tips' in response

    def test_search_offset(self):
        response = self.api.tips.search(params={'ll': self.default_geo, 'offset': 3})
        assert 'tips' in response

    def test_search_query(self):
        response = self.api.tips.search(params={'ll': self.default_geo, 'query': 'donuts'})
        assert 'tips' in response


    """
    Aspects
    """
    def test_done(self):
        response = self.api.tips.done(self.default_tipid)
        assert 'done' in response

    def test_done_limit(self):
        response = self.api.tips.done(self.default_tipid, params={'limit': 10})
        assert 'done' in response

    def test_done_offset(self):
        response = self.api.tips.done(self.default_tipid, params={'offset': 3})
        assert 'done' in response


    def test_listed(self):
        response = self.api.tips.listed(self.default_tipid)
        assert 'lists' in response

    def test_listed_group(self):
        response = self.api.tips.listed(self.default_tipid, params={'group': 'other'})
        assert 'lists' in response

########NEW FILE########
__FILENAME__ = test_users
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

import os

from . import TEST_DATA_DIR, BaseAuthenticatedEndpointTestCase



class UsersEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_user(self):
        response = self.api.users()
        assert 'user' in response

    def test_leaderboard(self):
        response = self.api.users.leaderboard()
        assert 'leaderboard' in response

    def test_leaderboard_limit(self):
        response = self.api.users.leaderboard(params={'neighbors': 5})
        assert 'leaderboard' in response

    def test_search_twitter(self):
        response = self.api.users.search(params={'twitter': u'mLewisLogic'})
        assert 'results' in response

    def test_search_name(self):
        response = self.api.users.search(params={'name': u'Mike'})
        assert 'results' in response

    def test_requests(self):
        response = self.api.users.requests()
        assert 'requests' in response

    """
    Aspects
    """
    def test_badges(self):
        response = self.api.users.badges()
        assert 'sets' in response
        assert 'badges' in response

    def test_checkins(self):
        response = self.api.users.checkins()
        assert 'checkins' in response

    def test_checkins_limit(self):
        response = self.api.users.checkins(params={'limit': 10})
        assert 'checkins' in response

    def test_checkins_offset(self):
        response = self.api.users.checkins(params={'offset': 3})
        assert 'checkins' in response

    def test_all_checkins(self):
        checkins = list(self.api.users.all_checkins())
        assert isinstance(checkins, list)

    def test_friends(self):
        response = self.api.users.friends()
        assert 'friends' in response

    def test_friends_limit(self):
        response = self.api.users.friends(params={'limit': 10})
        assert 'friends' in response

    def test_friends_offset(self):
        response = self.api.users.friends(params={'offset': 3})
        assert 'friends' in response

    def test_lists(self):
        response = self.api.users.lists()
        assert 'lists' in response

    def test_lists_friends(self):
        response = self.api.users.lists(params={'group': u'friends'})
        assert 'lists' in response

    def test_lists_suggested(self):
        response = self.api.users.lists(params={'group': u'suggested', 'll': self.default_geo})
        assert 'lists' in response

    def test_mayorships(self):
        response = self.api.users.mayorships()
        assert 'mayorships' in response

    def test_photos(self):
        response = self.api.users.photos()
        assert 'photos' in response

    def test_photos_limit(self):
        response = self.api.users.photos(params={'limit': 10})
        assert 'photos' in response

    def test_photos_offset(self):
        response = self.api.users.photos(params={'offset': 3})
        assert 'photos' in response

    def test_venuehistory(self):
        response = self.api.users.venuehistory()
        assert 'venues' in response

    """
    Actions
    """
    def test_update_name(self):
        # Change my name to Miguel
        response = self.api.users.update(params={'firstName': 'Miguel'})
        assert 'user' in response
        assert response['user']['firstName'] == 'Miguel'
        # Change it back
        response = self.api.users.update(params={'firstName': 'Mike'})
        assert 'user' in response
        assert response['user']['firstName'] == 'Mike'

    def test_update_photo(self):
        test_photo = os.path.join(TEST_DATA_DIR, 'profile_photo.jpg')
        # Fail gracefully if we don't have a test photo on disk
        if os.path.isfile(test_photo):
            photo_data = open(test_photo, 'r')
            try:
                response = self.api.users.update(photo_data=photo_data)
                assert 'user' in response
            finally:
                photo_data.close()
        else:
            print u"Put a 'test-photo.jpg' file in the testdata/ directory to enable this test."

########NEW FILE########
__FILENAME__ = test_venues
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis
import logging; log = logging.getLogger(__name__)

from . import BaseAuthenticatedEndpointTestCase, BaseUserlessEndpointTestCase



class VenuesEndpointTestCase(BaseAuthenticatedEndpointTestCase):
    """
    General
    """
    def test_venue(self):
        response = self.api.venues(self.default_venueid)
        assert 'venue' in response


    def test_categories(self):
        response = self.api.venues.categories()
        assert 'categories' in response


    def test_explore(self):
        response = self.api.venues.explore(params={'ll': self.default_geo})
        assert 'groups' in response

    def test_explore_radius(self):
        response = self.api.venues.explore(params={'ll': self.default_geo, 'radius': 30})
        assert 'groups' in response

    def test_explore_section(self):
        response = self.api.venues.explore(params={'ll': self.default_geo, 'section': u'café'})
        assert 'groups' in response

    def test_explore_query(self):
        response = self.api.venues.explore(params={'ll': self.default_geo, 'query': 'donuts'})
        assert 'groups' in response

    def test_explore_limit(self):
        response = self.api.venues.explore(params={'ll': self.default_geo, 'limit': 10})
        assert 'groups' in response

    def test_explore_intent(self):
        response = self.api.venues.explore(params={'ll': self.default_geo, 'intent': 'specials'})
        assert 'groups' in response


    def test_managed(self):
        response = self.api.venues.managed()
        assert 'venues' in response


    def test_search(self):
        response = self.api.venues.search(params={'ll': self.default_geo})
        assert 'venues' in response

    def test_search_query(self):
        response = self.api.venues.search(params={'ll': self.default_geo, 'query': 'donuts'})
        assert 'venues' in response

    def test_search_limit(self):
        response = self.api.venues.search(params={'ll': self.default_geo, 'limit': 10})
        assert 'venues' in response

    def test_search_browse(self):
        response = self.api.venues.search(params={'ll': self.default_geo, 'radius': self.default_geo_radius, 'intent': 'browse'})
        assert 'venues' in response


    def test_suggestcompletion(self):
        response = self.api.venues.suggestcompletion(params={'ll': self.default_geo, 'query': 'cof'})
        assert 'minivenues' in response


    def test_trending(self):
        response = self.api.venues.trending(params={'ll': self.default_geo})
        assert 'venues' in response

    def test_trending_limit(self):
        response = self.api.venues.trending(params={'ll': self.default_geo, 'limit': 10})
        assert 'venues' in response

    def test_trending_radius(self):
        response = self.api.venues.trending(params={'ll': self.default_geo, 'radius': 100})
        assert 'venues' in response


    """
    Aspects
    """
    def test_event(self):
        response = self.api.venues.events(self.default_venueid)
        assert 'events' in response


    def test_herenow(self):
        response = self.api.venues.herenow(self.default_venueid)
        assert 'hereNow' in response

    def test_herenow_limit(self):
        response = self.api.venues.herenow(self.default_venueid, params={'limit': 10})
        assert 'hereNow' in response

    def test_herenow_offset(self):
        response = self.api.venues.herenow(self.default_venueid, params={'offset': 3})
        assert 'hereNow' in response


    def test_listed(self):
        response = self.api.venues.listed(self.default_venueid)
        assert 'lists' in response

    def test_listed_group(self):
        response = self.api.venues.listed(self.default_venueid, params={'group': 'friends'})
        assert 'lists' in response

    def test_listed_limit(self):
        response = self.api.venues.listed(self.default_venueid, params={'limit': 10})
        assert 'lists' in response

    def test_listed_offset(self):
        response = self.api.venues.listed(self.default_venueid, params={'offset': 3})
        assert 'lists' in response


    def test_photos(self):
        response = self.api.venues.photos(self.default_venueid, params={'group': 'venue'})
        assert 'photos' in response

    def test_photos_limit(self):
        response = self.api.venues.photos(self.default_venueid, params={'limit': 10})
        assert 'photos' in response

    def test_photos_offset(self):
        response = self.api.venues.photos(self.default_venueid, params={'offset': 3})
        assert 'photos' in response


    def test_similar(self):
        response = self.api.venues.similar(self.default_venueid)
        assert 'similarVenues' in response


    def test_tips(self):
        response = self.api.venues.tips(self.default_venueid)
        assert 'tips' in response

    def test_tips_group(self):
        response = self.api.venues.tips(self.default_venueid, params={'sort': 'popular'})
        assert 'tips' in response

    def test_tips_limit(self):
        response = self.api.venues.tips(self.default_venueid, params={'limit': 10})
        assert 'tips' in response

    def test_tips_offset(self):
        response = self.api.venues.tips(self.default_venueid, params={'offset': 3})
        assert 'tips' in response



class VenuesUserlessEndpointTestCase(BaseUserlessEndpointTestCase):
    """
    General
    """
    def test_venue(self):
        response = self.api.venues(self.default_venueid)
        assert 'venue' in response


    def test_categories(self):
        response = self.api.venues.categories()
        assert 'categories' in response


    def test_explore(self):
        response = self.api.venues.explore(params={'ll': self.default_geo})
        assert 'groups' in response

    def test_explore_radius(self):
        response = self.api.venues.explore(params={'ll': self.default_geo, 'radius': 30})
        assert 'groups' in response

    def test_explore_section(self):
        response = self.api.venues.explore(params={'ll': self.default_geo, 'section': 'coffee'})
        assert 'groups' in response

    def test_explore_query(self):
        response = self.api.venues.explore(params={'ll': self.default_geo, 'query': 'donuts'})
        assert 'groups' in response

    def test_explore_limit(self):
        response = self.api.venues.explore(params={'ll': self.default_geo, 'limit': 10})
        assert 'groups' in response

    def test_explore_intent(self):
        response = self.api.venues.explore(params={'ll': self.default_geo, 'intent': 'specials'})
        assert 'groups' in response


    def test_search(self):
        response = self.api.venues.search(params={'ll': self.default_geo})
        assert 'venues' in response

    def test_search_query(self):
        response = self.api.venues.search(params={'ll': self.default_geo, 'query': 'donuts'})
        assert 'venues' in response

    def test_search_limit(self):
        response = self.api.venues.search(params={'ll': self.default_geo, 'limit': 10})
        assert 'venues' in response

    def test_search_browse(self):
        response = self.api.venues.search(params={'ll': self.default_geo, 'radius': self.default_geo_radius, 'intent': 'browse'})
        assert 'venues' in response

    def test_search_ampersand(self):
        response = self.api.venues.search(params={'query': u'Mirch Masala Restaurant & Bar', 'll': u'22.52,88.36'})
        assert 'venues' in response
        assert len(response['venues']) # Make sure there's at least one result


    def test_trending(self):
        response = self.api.venues.trending(params={'ll': self.default_geo})
        assert 'venues' in response

    def test_trending_limit(self):
        response = self.api.venues.trending(params={'ll': self.default_geo, 'limit': 10})
        assert 'venues' in response

    def test_trending_radius(self):
        response = self.api.venues.trending(params={'ll': self.default_geo, 'radius': 100})
        assert 'venues' in response


    """
    Aspects
    """
    def test_listed(self):
        response = self.api.venues.listed(self.default_venueid)
        assert 'lists' in response

    def test_listed_group(self):
        response = self.api.venues.listed(self.default_venueid, params={'group': 'other'})
        assert 'lists' in response

    def test_listed_limit(self):
        response = self.api.venues.listed(self.default_venueid, params={'limit': 10})
        assert 'lists' in response

    def test_listed_offset(self):
        response = self.api.venues.listed(self.default_venueid, params={'offset': 3})
        assert 'lists' in response


    def test_photos(self):
        response = self.api.venues.photos(self.default_venueid, params={'group': 'venue'})
        assert 'photos' in response

    def test_photos_limit(self):
        response = self.api.venues.photos(self.default_venueid, params={'limit': 10})
        assert 'photos' in response

    def test_photos_offset(self):
        response = self.api.venues.photos(self.default_venueid, params={'offset': 3})
        assert 'photos' in response


    def test_tips(self):
        response = self.api.venues.tips(self.default_venueid)
        assert 'tips' in response

    def test_tips_group(self):
        response = self.api.venues.tips(self.default_venueid, params={'sort': 'popular'})
        assert 'tips' in response

    def test_tips_limit(self):
        response = self.api.venues.tips(self.default_venueid, params={'limit': 10})
        assert 'tips' in response

    def test_tips_offset(self):
        response = self.api.venues.tips(self.default_venueid, params={'offset': 3})
        assert 'tips' in response

########NEW FILE########
__FILENAME__ = _creds.example
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# (c) 2014 Mike Lewis

CLIENT_ID = u'YOUR_CLIENT_ID'
CLIENT_SECRET = u'YOUR_CLIENT_SECRET'
ACCESS_TOKEN = u'EXAMPLE_USER_ACCESS_TOKEN'

########NEW FILE########
