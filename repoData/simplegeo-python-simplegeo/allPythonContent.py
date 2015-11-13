__FILENAME__ = config
MY_OAUTH_KEY = 'MY_OAUTH_KEY'
MY_OAUTH_SECRET = 'MY_OAUTH_SECRET'
API_HOST = 'api.simplegeo.com'
API_PORT = 80

########NEW FILE########
__FILENAME__ = test_context
#!/usr/bin/env python

import unittest
from decimal import Decimal
import random

from simplegeo import Client

import config

if config.MY_OAUTH_KEY == 'MY_OAUTH_KEY' or \
    config.MY_OAUTH_SECRET == 'MY_SECRET_KEY':
    raise Exception('Please provide the proper credentials in config.py.')

def random_lat_lon():
    return (random.uniform(34.27083595165, 45.706179285330855), random.uniform(-113.2470703125, -88.9892578125))

class ConsumptionTest(unittest.TestCase):
    def setUp(self):
        self.client = Client(config.MY_OAUTH_KEY, config.MY_OAUTH_SECRET, host=config.API_HOST, port=config.API_PORT)
        self.known_points = {
            'darrell_k_royal_stadium': {
                'lat': 30.283863,
                'lon': -97.732519,
                'expected_response': EXPECTED_RESPONSES['darrell_k_royal_stadium']
            },
            'att_park': {
                'lat': 37.778434,
                'lon': -122.389146,
                'expected_response': EXPECTED_RESPONSES['att_park']
            },
            'invesco_field': {
                'lat': 39.744026,
                'lon': -105.019893,
                'expected_response': EXPECTED_RESPONSES['invesco_field']
            }
        }

        # Request known points.
        self.known_requests = []
        for (point_name, point) in self.known_points.iteritems():
            point['name'] = point_name
            response = self.client.context.get_context(point['lat'], point['lon'])
            self.known_points[point_name]['response'] = response
            self.known_requests.append((point, response))

        # Request random points.
        self.random_requests = []
        for i in range(10):
            (lat, lon) = random_lat_lon()
            point = {'lat': lat, 'lon': lon}
            response = self.client.context.get_context(lat, lon)
            self.random_requests.append((point, response))

    """
    def test_weather(self):
        # Invesco Field should have the weather data.
        point = self.known_points['invesco_field']
        response = point['response']

        self.assertTrue('weather' in response, 'Weather not contained in response for point %s,%s' % (point['lat'], point['lon']))
        self.assertTrue('temperature' in response['weather'], 'Temperature not found in weather in response for point %s,%s' % (point['lat'], point['lon']))
        self.assertEqual(response['weather']['temperature'][-1:], 'F', 'Temperature value %s does not end in F in response for %s,%s' % (response['weather']['temperature'], point['lat'], point['lon']))
    """

    def test_demographics(self):
        # Invesco Field should have the demographic data.
        point = self.known_points['invesco_field']
        response = point['response']

        self.assertTrue('demographics' in response, 'Demographics not found in response for point %s,%s' % (point['lat'], point['lon']))
        self.assertTrue('metro_score' in response['demographics'], 'metro_score not found in demographics section for point %s,%s' % (point['lat'], point['lon']))
        self.assertTrue(0 <= int(response['demographics']['metro_score']) <= 10, 'Invalid value "%s" for metro_score in response for point %s,%s' % (response['demographics']['metro_score'], point['lat'], point['lon']))

    def test_expected_features_are_received(self):
        # Test that all features expected are received
        for (point, response) in self.known_requests:
            for expected_feature in point['expected_response']['features']:
                found_expected_feature = False
                for received_feature in response['features']:
                    if expected_feature == received_feature:
                        found_expected_feature = True
                self.assertTrue(found_expected_feature, 'Could not find expected feature in response for point %s,%s:\n%s' % (point['lat'], point['lon'], expected_feature))

    def test_received_features_are_expected(self):
        # Test that all features received are expected
        for (point, response) in self.known_requests:
            for received_feature in response['features']:
                found_received_feature = False
                for expected_feature in point['expected_response']['features']:
                    if received_feature == expected_feature:
                        found_received_feature = True
                self.assertTrue(found_received_feature, 'Could not find received feature in response for point %s,%s:\n%s' % (point['lat'], point['lon'], received_feature))

    def test_duplicate_handles(self):
        # Tests random requests and known requests.
        for (point, response) in self.known_requests + self.random_requests:
            for (i, feature) in enumerate(response['features']):
                for (j, possible_duplicate_feature) in enumerate(response['features']):
                    if i != j:
                        self.assertNotEqual(feature['handle'], possible_duplicate_feature['handle'], 'Found duplicate handle %s for point %s,%s' % (feature['handle'], point['lat'], point['lon']))
                        # Test for dupes in the first 25 characters of the handle.
                        self.assertNotEqual(feature['handle'][:25], possible_duplicate_feature['handle'][:25], 'Found duplicate *base* handle %s for point %s,%s' % (feature['handle'][:25], point['lat'], point['lon']))

    def test_duplicate_categories(self):
        # Ensure that we don't have multiple features with specified type/category/subcategory configurations.
        dupe_classifiers = [{'type': 'Region',
                             'category': 'Subnational',
                              'subcategory': 'State'},
                             {'type': 'Region',
                              'category': 'Time Zone',
                              'subcategory': ''},
                             {'type': 'Region',
                              'category': 'National',
                              'subcategory': ''},
                             {'type': 'Region',
                              'category': 'Urban Area',
                              'subcategory': ''},
                             {'type': 'Region',
                              'category': 'US Census',
                              'subcategory': 'Tract'},
                             {'type': 'Region',
                              'category': 'Neighborhood',
                              'subcategory': ''},
                             {'type': 'Region',
                              'category': 'Administrative',
                              'subcategory': 'County'},
                             {'type': 'Region',
                              'category': 'Municiple',
                              'subcategory': 'City'},
                             {'type': 'Region',
                              'category': 'School District',
                              'subcategory': 'Unified'}]
        for (point, response) in self.known_requests:
            for dupe_classifier in dupe_classifiers:
                instances_found = 0
                for feature in response['features']:
                    for classifier in feature['classifiers']:
                        if 'type' in classifier and 'category' in classifier and 'subcategory' in classifier:
                            if dupe_classifier['type'] == classifier['type'] and dupe_classifier['category'] == classifier['category'] and dupe_classifier['subcategory'] == classifier['subcategory']:
                                instances_found += 1
                                self.assertTrue(instances_found <= 1, 'Found dupe for type/categories %s/%s/%s for point %s,%s' % (dupe_classifier['type'], dupe_classifier['category'], dupe_classifier['subcategory'], point['lat'], point['lon']))


EXPECTED_RESPONSES = {
    'darrell_k_royal_stadium': {'demographics': {'metro_score': 9},
 'features': [{'abbr': None,
               'attribution': '(c) OpenStreetMap (http://openstreetmap.org/) and contributors',
               'bounds': [Decimal('-97.733787'),
                          Decimal('30.282636'),
                          Decimal('-97.731332'),
                          Decimal('30.284719')],
               'classifiers': [{'category': 'Arena',
                                'subcategory': 'Stadium',
                                'type': 'Entertainment'}],
               'handle': 'SG_7QeOhXR4dptALoERMRWlBX_30.283681_-97.732557',
               'href': 'http://api.simplegeo.com/1.0/features/SG_7QeOhXR4dptALoERMRWlBX_30.283681_-97.732557.json',
               'license': 'http://creativecommons.org/licenses/by-sa/2.0/',
               'name': 'Darrell K Royal-Texas Memorial Stadium'},
              {'abbr': None,
               'bounds': [Decimal('-97.735709'),
                          Decimal('30.278506'),
                          Decimal('-97.72013'),
                          Decimal('30.297486')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'Municipal',
                                'type': 'Region'}],
               'handle': 'SG_2WMamKxH8LWbSagvs7rnXT_30.288060_-97.728167',
               'href': 'http://api.simplegeo.com/1.0/features/SG_2WMamKxH8LWbSagvs7rnXT_30.288060_-97.728167.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': '0146'},
              {'abbr': None,
               'attribution': '(c) OpenStreetMap (http://openstreetmap.org/) and contributors',
               'bounds': [Decimal('-97.741897'),
                          Decimal('30.274778'),
                          Decimal('-97.721764'),
                          Decimal('30.291944')],
               'classifiers': [{'category': 'Education',
                                'subcategory': 'University',
                                'type': 'Public Place'}],
               'handle': 'SG_5UcxGK9eJy1osUXXnZ40qt_30.284078_-97.732866',
               'href': 'http://api.simplegeo.com/1.0/features/SG_5UcxGK9eJy1osUXXnZ40qt_30.284078_-97.732866.json',
               'license': 'http://creativecommons.org/licenses/by-sa/2.0/',
               'name': 'The University of Texas At Austin'},
              {'abbr': None,
               'bounds': [Decimal('-97.741983'),
                          Decimal('30.274908'),
                          Decimal('-97.721882'),
                          Decimal('30.293307')],
               'classifiers': [{'category': 'Neighborhood',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_09DvIpGFBF83IitqjJBDWf_30.284313_-97.733270',
               'href': 'http://api.simplegeo.com/1.0/features/SG_09DvIpGFBF83IitqjJBDWf_30.284313_-97.733270.json',
               'license': 'Not For Redistribution',
               'name': 'UT'},
              {'abbr': None,
               'bounds': [Decimal('-97.735709'),
                          Decimal('30.278506'),
                          Decimal('-97.713564'),
                          Decimal('30.297486')],
               'classifiers': [{'category': 'US Census',
                                'subcategory': 'Tract',
                                'type': 'Region'}],
               'handle': 'SG_6USdLOhEJwISEW5pfgl6qP_30.288248_-97.725055',
               'href': 'http://api.simplegeo.com/1.0/features/SG_6USdLOhEJwISEW5pfgl6qP_30.288248_-97.725055.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': '48453000401'},
              {'abbr': None,
               'bounds': [Decimal('-97.753314'),
                          Decimal('30.278506'),
                          Decimal('-97.72013'),
                          Decimal('30.313464')],
               'classifiers': [{'category': 'Postal Code',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_1D0rEwHouPxhMPykjtb5RJ_30.293195_-97.737870',
               'href': 'http://api.simplegeo.com/1.0/features/SG_1D0rEwHouPxhMPykjtb5RJ_30.293195_-97.737870.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': '78705'},
              {'abbr': None,
               'bounds': [Decimal('-97.8154'),
                          Decimal('30.185101'),
                          Decimal('-97.70943'),
                          Decimal('30.378682')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'Provincial (Lower)',
                                'type': 'Region'}],
               'handle': 'SG_2kEgzBBtkatRD7DftdcXik_30.282104_-97.755901',
               'href': 'http://api.simplegeo.com/1.0/features/SG_2kEgzBBtkatRD7DftdcXik_30.282104_-97.755901.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'State House District 49'},
              {'abbr': None,
               'bounds': [Decimal('-98.011413'),
                          Decimal('30.097099'),
                          Decimal('-97.620842'),
                          Decimal('30.438391')],
               'classifiers': [{'category': 'School District',
                                'subcategory': 'Unified',
                                'type': 'Region'}],
               'handle': 'SG_4EckCuhVNcdrWNqLOht2oV_30.260705_-97.798455',
               'href': 'http://api.simplegeo.com/1.0/features/SG_4EckCuhVNcdrWNqLOht2oV_30.260705_-97.798455.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Austin Independent School District'},
              {'abbr': None,
               'bounds': [Decimal('-97.916667'),
                          Decimal('30.116667'),
                          Decimal('-97.591667'),
                          Decimal('30.591667')],
               'classifiers': [{'category': 'Urban Area',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_6WQD51qQfl7wkULHpoguiD_30.359587_-97.750655',
               'href': 'http://api.simplegeo.com/1.0/features/SG_6WQD51qQfl7wkULHpoguiD_30.359587_-97.750655.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Austin'},
              {'abbr': None,
               'bounds': [Decimal('-97.938383'),
                          Decimal('30.098659'),
                          Decimal('-97.561489'),
                          Decimal('30.516863')],
               'classifiers': [{'category': 'Municipal',
                                'subcategory': 'City',
                                'type': 'Region'}],
               'handle': 'SG_41bcEmeot99NfzPUAEmAth_30.306437_-97.754767',
               'href': 'http://api.simplegeo.com/1.0/features/SG_41bcEmeot99NfzPUAEmAth_30.306437_-97.754767.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Austin'},
              {'abbr': None,
               'bounds': [Decimal('-98.172977'),
                          Decimal('30.078246'),
                          Decimal('-97.369248'),
                          Decimal('30.628249')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'Provincial (Upper)',
                                'type': 'Region'}],
               'handle': 'SG_0FmGCHgubdRzXdEgP7lBHv_30.354295_-97.780522',
               'href': 'http://api.simplegeo.com/1.0/features/SG_0FmGCHgubdRzXdEgP7lBHv_30.354295_-97.780522.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'State Senate District 14'},
              {'abbr': None,
               'bounds': [Decimal('-98.172977'),
                          Decimal('30.024499'),
                          Decimal('-97.369248'),
                          Decimal('30.628249')],
               'classifiers': [{'category': 'Administrative',
                                'subcategory': 'County',
                                'type': 'Region'}],
               'handle': 'SG_1CMF3cFYwUnu109LStqa0u_30.334692_-97.781954',
               'href': 'http://api.simplegeo.com/1.0/features/SG_1CMF3cFYwUnu109LStqa0u_30.334692_-97.781954.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Travis'},
              {'abbr': None,
               'bounds': [Decimal('-100.063741'),
                          Decimal('29.382713'),
                          Decimal('-97.72013'),
                          Decimal('30.628249')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'National',
                                'type': 'Region'}],
               'handle': 'SG_0tdGOSJRQVasZaSWM3MKu6_29.970610_-98.918685',
               'href': 'http://api.simplegeo.com/1.0/features/SG_0tdGOSJRQVasZaSWM3MKu6_29.970610_-98.918685.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Congressional District 21'},
              {'abbr': 'TX',
               'bounds': [Decimal('-106.645646'),
                          Decimal('25.837164'),
                          Decimal('-93.508039'),
                          Decimal('36.500704')],
               'classifiers': [{'category': 'Subnational',
                                'subcategory': 'State',
                                'type': 'Region'}],
               'handle': 'SG_0X40atqKxLyVduZutLTA5S_31.447218_-99.317129',
               'href': 'http://api.simplegeo.com/1.0/features/SG_0X40atqKxLyVduZutLTA5S_31.447218_-99.317129.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Texas'},
              {'abbr': None,
               'bounds': [Decimal('-104.983027'),
                          Decimal('25.835548'),
                          Decimal('-84.659531'),
                          Decimal('49.388611')],
               'classifiers': [{'category': 'Time Zone',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_7jM3lCPI7D04dgq6Yglzpn_37.960280_-94.829481',
               'href': 'http://api.simplegeo.com/1.0/features/SG_7jM3lCPI7D04dgq6Yglzpn_37.960280_-94.829481.json',
               'license': 'creativecommons.org/publicdomain/zero/1.0/',
               'name': 'America/Chicago'},
              {'abbr': None,
               'bounds': [Decimal('-179.142471'),
                          Decimal('18.930138'),
                          Decimal('179.78115'),
                          Decimal('71.41218')],
               'classifiers': [{'category': 'National',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_3uwSAEdXVBzK1ZER9Nqkdp_45.687160_-112.493107',
               'href': 'http://api.simplegeo.com/1.0/features/SG_3uwSAEdXVBzK1ZER9Nqkdp_45.687160_-112.493107.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'United States of America'}],
 'query': {'latitude': Decimal('30.283863'),
           'longitude': Decimal('-97.732519')},
 'timestamp': Decimal('1298597802.802')},
    'att_park': {'demographics': {'metro_score': 10},
 'features': [{'abbr': None,
               'attribution': '(c) OpenStreetMap (http://openstreetmap.org/) and contributors',
               'bounds': [Decimal('-122.39115'),
                          Decimal('37.777233'),
                          Decimal('-122.387775'),
                          Decimal('37.779731')],
               'classifiers': [{'category': 'Arena',
                                'subcategory': 'Stadium',
                                'type': 'Entertainment'}],
               'handle': 'SG_4H2GqJDZrc0ZAjKGR8qM4D_37.778406_-122.389506',
               'href': 'http://api.simplegeo.com/1.0/features/SG_4H2GqJDZrc0ZAjKGR8qM4D_37.778406_-122.389506.json',
               'license': 'http://creativecommons.org/licenses/by-sa/2.0/',
               'name': 'AT&T Park'},
              {'abbr': None,
               'bounds': [Decimal('-122.398281'),
                          Decimal('37.777029'),
                          Decimal('-122.384281'),
                          Decimal('37.796503')],
               'classifiers': [{'category': 'Neighborhood',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_6Bv7Cw61hmZjfZ8McTGGM2_37.785379_-122.390793',
               'href': 'http://api.simplegeo.com/1.0/features/SG_6Bv7Cw61hmZjfZ8McTGGM2_37.785379_-122.390793.json',
               'license': 'Not For Redistribution',
               'name': 'South Beach'},
              {'abbr': None,
               'bounds': [Decimal('-122.40499'),
                          Decimal('37.764379'),
                          Decimal('-122.379681'),
                          Decimal('37.783529')],
               'classifiers': [{'category': 'US Census',
                                'subcategory': 'Tract',
                                'type': 'Region'}],
               'handle': 'SG_3JxiYHuWo7N9KDYeDSijzl_37.772749_-122.390793',
               'href': 'http://api.simplegeo.com/1.0/features/SG_3JxiYHuWo7N9KDYeDSijzl_37.772749_-122.390793.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': '06075060700'},
              {'abbr': None,
               'bounds': [Decimal('-122.406493'),
                          Decimal('37.749358'),
                          Decimal('-122.379202'),
                          Decimal('37.789791')],
               'classifiers': [{'category': 'Postal Code',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_4iNdS13pIvPoUBWBnq0U2f_37.766945_-122.393570',
               'href': 'http://api.simplegeo.com/1.0/features/SG_4iNdS13pIvPoUBWBnq0U2f_37.766945_-122.393570.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': '94107'},
              {'abbr': None,
               'bounds': [Decimal('-122.546386'),
                          Decimal('37.70823'),
                          Decimal('-122.28178'),
                          Decimal('37.929824')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'Provincial (Lower)',
                                'type': 'Region'}],
               'handle': 'SG_4gzxFRgOF9YjFAtAiQFpDC_37.793367_-122.397153',
               'href': 'http://api.simplegeo.com/1.0/features/SG_4gzxFRgOF9YjFAtAiQFpDC_37.793367_-122.397153.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Assembly District 13'},
              {'abbr': None,
               'bounds': [Decimal('-122.612285'),
                          Decimal('37.708131'),
                          Decimal('-122.28178'),
                          Decimal('37.929824')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'National',
                                'type': 'Region'}],
               'handle': 'SG_2WBEyBsRAqLAHw1QuqXTv1_37.787198_-122.429550',
               'href': 'http://api.simplegeo.com/1.0/features/SG_2WBEyBsRAqLAHw1QuqXTv1_37.787198_-122.429550.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Congressional District 8'},
              {'abbr': None,
               'bounds': [Decimal('-123.173825'),
                          Decimal('37.63983'),
                          Decimal('-122.28178'),
                          Decimal('37.929824')],
               'classifiers': [{'category': 'Administrative',
                                'subcategory': 'County',
                                'type': 'Region'}],
               'handle': 'SG_7TAYWdlPlAIzUDT7MVwxmZ_37.759717_-122.693971',
               'href': 'http://api.simplegeo.com/1.0/features/SG_7TAYWdlPlAIzUDT7MVwxmZ_37.759717_-122.693971.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'San Francisco'},
              {'abbr': None,
               'bounds': [Decimal('-123.173825'),
                          Decimal('37.63983'),
                          Decimal('-122.28178'),
                          Decimal('37.929824')],
               'classifiers': [{'category': 'Municipal',
                                'subcategory': 'City',
                                'type': 'Region'}],
               'handle': 'SG_1mNfKHr5aXH7LWgmZL8Uq7_37.759717_-122.693971',
               'href': 'http://api.simplegeo.com/1.0/features/SG_1mNfKHr5aXH7LWgmZL8Uq7_37.759717_-122.693971.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'San Francisco'},
              {'abbr': None,
               'bounds': [Decimal('-123.173825'),
                          Decimal('37.63983'),
                          Decimal('-122.28178'),
                          Decimal('37.929824')],
               'classifiers': [{'category': 'School District',
                                'subcategory': 'Unified',
                                'type': 'Region'}],
               'handle': 'SG_4wyrIh6TQId1MiL2cfYa5d_37.759717_-122.693971',
               'href': 'http://api.simplegeo.com/1.0/features/SG_4wyrIh6TQId1MiL2cfYa5d_37.759717_-122.693971.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'San Francisco Unified School District'},
              {'abbr': None,
               'bounds': [Decimal('-122.516667'),
                          Decimal('37.191667'),
                          Decimal('-121.733333'),
                          Decimal('38.041667')],
               'classifiers': [{'category': 'Urban Area',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_4n4ze6xOdAFr0gp1WboZrN_37.551206_-122.127401',
               'href': 'http://api.simplegeo.com/1.0/features/SG_4n4ze6xOdAFr0gp1WboZrN_37.551206_-122.127401.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'San Francisco'},
              {'abbr': None,
               'bounds': [Decimal('-123.134523'),
                          Decimal('37.70823'),
                          Decimal('-122.28178'),
                          Decimal('38.532067')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'Provincial (Upper)',
                                'type': 'Region'}],
               'handle': 'SG_1wm1YKOa9HLv5VI8IbHVW7_38.107525_-122.693633',
               'href': 'http://api.simplegeo.com/1.0/features/SG_1wm1YKOa9HLv5VI8IbHVW7_38.107525_-122.693633.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'State Senate District 3'},
              {'abbr': 'CA',
               'bounds': [Decimal('-124.482003'),
                          Decimal('32.528832'),
                          Decimal('-114.131211'),
                          Decimal('42.009517')],
               'classifiers': [{'category': 'Subnational',
                                'subcategory': 'State',
                                'type': 'Region'}],
               'handle': 'SG_2MySaPILVQG3MoXrsVehyR_37.215297_-119.663837',
               'href': 'http://api.simplegeo.com/1.0/features/SG_2MySaPILVQG3MoXrsVehyR_37.215297_-119.663837.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'California'},
              {'abbr': None,
               'bounds': [Decimal('-124.733253'),
                          Decimal('32.534622'),
                          Decimal('-114.039345'),
                          Decimal('49.002892')],
               'classifiers': [{'category': 'Time Zone',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_3tLT0I5cOUWIpoVOBeScOx_41.316130_-119.116571',
               'href': 'http://api.simplegeo.com/1.0/features/SG_3tLT0I5cOUWIpoVOBeScOx_41.316130_-119.116571.json',
               'license': 'creativecommons.org/publicdomain/zero/1.0/',
               'name': 'America/Los_Angeles'},
              {'abbr': None,
               'bounds': [Decimal('-179.142471'),
                          Decimal('18.930138'),
                          Decimal('179.78115'),
                          Decimal('71.41218')],
               'classifiers': [{'category': 'National',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_3uwSAEdXVBzK1ZER9Nqkdp_45.687160_-112.493107',
               'href': 'http://api.simplegeo.com/1.0/features/SG_3uwSAEdXVBzK1ZER9Nqkdp_45.687160_-112.493107.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'United States of America'}],
 'query': {'latitude': Decimal('37.778434'),
           'longitude': Decimal('-122.389146')},
 'timestamp': Decimal('1298598091.119')},
    'invesco_field': {'demographics': {'metro_score': 9},
 'features': [{'abbr': None,
               'attribution': '(c) OpenStreetMap (http://openstreetmap.org/) and contributors',
               'bounds': [Decimal('-105.021684'),
                          Decimal('39.742624'),
                          Decimal('-105.018423'),
                          Decimal('39.745146')],
               'classifiers': [{'category': 'Arena',
                                'subcategory': 'Stadium',
                                'type': 'Entertainment'}],
               'handle': 'SG_2fVsRKtErbeZJcs52XUwIk_39.743886_-105.020051',
               'href': 'http://api.simplegeo.com/1.0/features/SG_2fVsRKtErbeZJcs52XUwIk_39.743886_-105.020051.json',
               'license': 'http://creativecommons.org/licenses/by-sa/2.0/',
               'name': 'Invesco Field at Mile High'},
              {'abbr': None,
               'bounds': [Decimal('-105.025225'),
                          Decimal('39.725319'),
                          Decimal('-105.015637'),
                          Decimal('39.747599')],
               'classifiers': [{'category': 'US Census',
                                'subcategory': 'Tract',
                                'type': 'Region'}],
               'handle': 'SG_3O7majtYm480OLz6Tb5loy_39.735809_-105.021085',
               'href': 'http://api.simplegeo.com/1.0/features/SG_3O7majtYm480OLz6Tb5loy_39.735809_-105.021085.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': '08031000800'},
              {'abbr': None,
               'bounds': [Decimal('-105.025338'),
                          Decimal('39.725233'),
                          Decimal('-105.015621'),
                          Decimal('39.747498')],
               'classifiers': [{'category': 'Neighborhood',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_5aIM28l5oK5UCmVC2O4huP_39.735617_-105.021119',
               'href': 'http://api.simplegeo.com/1.0/features/SG_5aIM28l5oK5UCmVC2O4huP_39.735617_-105.021119.json',
               'license': 'Not For Redistribution',
               'name': 'Sun Valley'},
              {'abbr': None,
               'bounds': [Decimal('-105.025299'),
                          Decimal('39.740148'),
                          Decimal('-104.995989'),
                          Decimal('39.760591')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'Municipal',
                                'type': 'Region'}],
               'handle': 'SG_1dcdZehYzJrj8RGTRP0TDS_39.749147_-105.012482',
               'href': 'http://api.simplegeo.com/1.0/features/SG_1dcdZehYzJrj8RGTRP0TDS_39.749147_-105.012482.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Precinct 519'},
              {'abbr': None,
               'bounds': [Decimal('-105.038162'),
                          Decimal('39.743451'),
                          Decimal('-104.997607'),
                          Decimal('39.784227')],
               'classifiers': [{'category': 'Postal Code',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_1RtJ8mJUCkX90AiKEScBp6_39.767096_-105.019932',
               'href': 'http://api.simplegeo.com/1.0/features/SG_1RtJ8mJUCkX90AiKEScBp6_39.767096_-105.019932.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': '80211'},
              {'abbr': None,
               'bounds': [Decimal('-105.025299'),
                          Decimal('39.726943'),
                          Decimal('-104.939882'),
                          Decimal('39.798396')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'Provincial (Lower)',
                                'type': 'Region'}],
               'handle': 'SG_7DAY51W0SWg0IXwHiwFjoW_39.765839_-104.988528',
               'href': 'http://api.simplegeo.com/1.0/features/SG_7DAY51W0SWg0IXwHiwFjoW_39.765839_-104.988528.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'State House District 5'},
              {'abbr': None,
               'bounds': [Decimal('-105.065248'),
                          Decimal('39.689431'),
                          Decimal('-104.997452'),
                          Decimal('39.794066')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'Provincial (Upper)',
                                'type': 'Region'}],
               'handle': 'SG_5HDVOJwxs9AY2aNnXPH5S6_39.744858_-105.030781',
               'href': 'http://api.simplegeo.com/1.0/features/SG_5HDVOJwxs9AY2aNnXPH5S6_39.744858_-105.030781.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'State Senate District 34'},
              {'abbr': None,
               'bounds': [Decimal('-105.109927'),
                          Decimal('39.614337'),
                          Decimal('-104.600302'),
                          Decimal('39.914247')],
               'classifiers': [{'category': 'Legislative District',
                                'subcategory': 'National',
                                'type': 'Region'}],
               'handle': 'SG_0dadIT0rGkpZwo2t7UgqfO_39.750246_-104.885585',
               'href': 'http://api.simplegeo.com/1.0/features/SG_0dadIT0rGkpZwo2t7UgqfO_39.750246_-104.885585.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Congressional District 1'},
              {'abbr': None,
               'bounds': [Decimal('-105.109927'),
                          Decimal('39.614337'),
                          Decimal('-104.600302'),
                          Decimal('39.914247')],
               'classifiers': [{'category': 'Administrative',
                                'subcategory': 'County',
                                'type': 'Region'}],
               'handle': 'SG_0aSGDuSeDtvIzbPrdgVMoN_39.762168_-104.875849',
               'href': 'http://api.simplegeo.com/1.0/features/SG_0aSGDuSeDtvIzbPrdgVMoN_39.762168_-104.875849.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Denver'},
              {'abbr': None,
               'bounds': [Decimal('-105.109927'),
                          Decimal('39.614337'),
                          Decimal('-104.600302'),
                          Decimal('39.914247')],
               'classifiers': [{'category': 'Municipal',
                                'subcategory': 'City',
                                'type': 'Region'}],
               'handle': 'SG_5mkJIHfzh3DmXAVkL5ns7C_39.762168_-104.875849',
               'href': 'http://api.simplegeo.com/1.0/features/SG_5mkJIHfzh3DmXAVkL5ns7C_39.762168_-104.875849.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Denver'},
              {'abbr': None,
               'bounds': [Decimal('-105.109927'),
                          Decimal('39.614337'),
                          Decimal('-104.600302'),
                          Decimal('39.914247')],
               'classifiers': [{'category': 'School District',
                                'subcategory': 'Unified',
                                'type': 'Region'}],
               'handle': 'SG_522ZsELgQtfLcbMKoMPAay_39.762161_-104.875858',
               'href': 'http://api.simplegeo.com/1.0/features/SG_522ZsELgQtfLcbMKoMPAay_39.762161_-104.875858.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Denver County School District 1'},
              {'abbr': None,
               'bounds': [Decimal('-105.241667'),
                          Decimal('39.5'),
                          Decimal('-104.708333'),
                          Decimal('40.025')],
               'classifiers': [{'category': 'Urban Area',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_3qkMPICG5pMFYrBwTKJDec_39.731190_-104.984183',
               'href': 'http://api.simplegeo.com/1.0/features/SG_3qkMPICG5pMFYrBwTKJDec_39.731190_-104.984183.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Denver'},
              {'abbr': 'CO',
               'bounds': [Decimal('-109.066811'),
                          Decimal('36.992424'),
                          Decimal('-102.040878'),
                          Decimal('41.003444')],
               'classifiers': [{'category': 'Subnational',
                                'subcategory': 'State',
                                'type': 'Region'}],
               'handle': 'SG_3V8cOXsDm6WVfNAC3GYJpr_38.998545_-105.547826',
               'href': 'http://api.simplegeo.com/1.0/features/SG_3V8cOXsDm6WVfNAC3GYJpr_38.998545_-105.547826.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'Colorado'},
              {'abbr': None,
               'bounds': [Decimal('-116.050735'),
                          Decimal('30.628255'),
                          Decimal('-100.260872'),
                          Decimal('49.000771')],
               'classifiers': [{'category': 'Time Zone',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_4nMNM1ah9tMVutXTI8wSCB_41.330677_-107.469772',
               'href': 'http://api.simplegeo.com/1.0/features/SG_4nMNM1ah9tMVutXTI8wSCB_41.330677_-107.469772.json',
               'license': 'creativecommons.org/publicdomain/zero/1.0/',
               'name': 'America/Denver'},
              {'abbr': None,
               'bounds': [Decimal('-179.142471'),
                          Decimal('18.930138'),
                          Decimal('179.78115'),
                          Decimal('71.41218')],
               'classifiers': [{'category': 'National',
                                'subcategory': None,
                                'type': 'Region'}],
               'handle': 'SG_3uwSAEdXVBzK1ZER9Nqkdp_45.687160_-112.493107',
               'href': 'http://api.simplegeo.com/1.0/features/SG_3uwSAEdXVBzK1ZER9Nqkdp_45.687160_-112.493107.json',
               'license': 'http://creativecommons.org/publicdomain/mark/1.0/',
               'name': 'United States of America'}],
 'query': {'latitude': Decimal('39.744026'),
           'longitude': Decimal('-105.019893')},
 'timestamp': Decimal('1298597942.41')},
}


if __name__ == '__main__':
        unittest.main()

########NEW FILE########
__FILENAME__ = test_storage
import time
import random
import unittest
from decimal import Decimal as D

import simplegeo.json as json

from simplegeo import Client
from simplegeo.models import Record, Layer
from simplegeo.util import APIError

import config

if config.MY_OAUTH_KEY == 'MY_OAUTH_KEY' or \
    config.MY_OAUTH_SECRET == 'MY_SECRET_KEY':
    raise Exception('Please provide the proper credentials in config.py.')

API_VERSION = '0.1'

TESTING_LAT = '37.7481624945'
TESTING_LON = '-122.433287165'
TESTING_IP_ADDRESS = '173.164.32.246'

TESTING_LAT_NON_US = '48.8566667'
TESTING_LON_NON_US = '2.3509871'
RECORD_TYPES = ['person', 'place', 'object']
TESTING_BOUNDS = [-122.43409, 37.747296999999996, -122.424768, 37.751841999999996]


class ClientTest(unittest.TestCase):

    def tearDown(self):
        for record in self.created_records:
            try:
                self.client.storage.delete_record(record.layer, record.id)
            except APIError, e:
                # If we get a 404, then our job is done.
                pass
        self._delete_test_layer()

    def setUp(self):
        self.client = Client(config.MY_OAUTH_KEY, config.MY_OAUTH_SECRET, host=config.API_HOST, port=config.API_PORT)
        self.created_records = []
        self._create_test_layer()

    def _create_test_layer(self):
        self.layer = Layer('test.layer.' + config.MY_OAUTH_KEY,
                           'Layer for Tests', 'Layer for \
                            Tests', False, ['http://simplegeo.com',
                            'http://example.com'])
        response = self.client.storage.create_layer(self.layer)
        self.assertEquals(response, {'status': 'OK'})
        response = self.client.storage.get_layer(self.layer.name)
        self.assertEquals(response['name'], self.layer.name)
        self.assertEquals(response['title'], self.layer.title)
        self.assertEquals(response['description'], self.layer.description)
        self.assertEquals(response['callback_urls'], self.layer.callback_urls)
        self.assertEquals(response['public'], self.layer.public)
        self.assert_(response['created'])
        self.assert_(response['updated'])

    def _delete_test_layer(self):
        response = self.client.storage.delete_layer(self.layer.name)
        self.assertEquals(response, {'status': 'Deleted'})
        self.assertRaises(APIError, self.client.storage.get_layer, self.layer.name)

    def _record(self):
        """ Generate a record in San Francisco. """
        top_left = [37.801646236899785, -122.47833251953125]
        bottom_right = [37.747371884118664, -122.3931884765625]

        record = Record(
            layer=self.layer.name,
            id=str(int(random.random() * 1000000)),
            lat=str(random.uniform(top_left[0], bottom_right[0])),
            lon=str(random.uniform(top_left[1], bottom_right[1])),
            type=RECORD_TYPES[random.randint(0, 2)]
        )
        return record

    def test_multi_record_post(self):
        post_records = [self._record() for i in range(10)]
        self.addRecordsAndSleep(self.layer.name, post_records)

        get_records = self.client.storage.get_records(self.layer.name,
                        [record.id for record in post_records])
        self.assertEquals(len(get_records), len(post_records))

        post_record_ids = [post_record.id for post_record in post_records]
        for get_record in get_records:
            self.assertTrue(get_record['id'] in post_record_ids)

    def test_too_many_records(self):
        record_limit = 100
        records = []
        for i in range(record_limit + 1):
            records.append(self._record())

        self.assertRaises(APIError, self.client.storage.add_records, self.layer.name,
                          records)

    def test_add_record(self):
        record = self._record()
        self.addRecordAndSleep(record)
        result = self.client.storage.get_record(record.layer, record.id)
        self.assertPointIsRecord(result, record)

    def test_add_update_delete_record(self):
        record = self._record()
        self.addRecordAndSleep(record)
        result = self.client.storage.get_record(record.layer, record.id)
        self.assertPointIsRecord(result, record)
        updated_record = self._record()
        updated_record.id = record.id
        self.addRecordAndSleep(updated_record)
        updated_result = self.client.storage.get_record(record.layer, record.id)
        self.assertPointIsRecord(updated_result, updated_record)
        self.client.storage.delete_record(record.layer, record.id)
        time.sleep(5)
        self.assertRaises(APIError, self.client.storage.get_record, record.layer, record.id)
        self.assertRaises(APIError, self.client.storage.get_record, updated_record.layer, updated_record.id)

    def test_record_history(self):
        post_records = [self._record() for i in range(10)]
        current_time = int(time.time())
        for record in post_records:
            record.id = post_records[0].id
            record.created = current_time
            current_time -= 1

        self.addRecordsAndSleep(self.layer.name, post_records)

        history = self.client.storage.get_history(self.layer.name, post_records[0].id)
        points = history.get('geometries')
        self.assertEquals(len(points), 10)

        count = 0
        for point in points:
            self.assertEquals(str(point.get('coordinates')[0]), post_records[count].lon)
            self.assertEquals(str(point.get('coordinates')[1]), post_records[count].lat)
            count += 1

    """ Waiting on Gate
    def test_nearby_ip_address_search(self):
        limit = 5
        records = []
        for i in range(limit):
            record = self._record()
            record.lat = float(39.7437) + (i / 10000000)
            record.lon = float(-104.9793) - (i / 10000000)
            records.append(record)

        self.addRecordsAndSleep(self.layer.name, records)

        nearby_result = self.client.get_nearby_ip_address(self.layer.name, TESTING_IP_ADDRESS, limit=limit, radius=10)

        features = nearby_result.get('features')
        self.assertEquals(len(features), limit)
    """


    # Layer Management

    def test_update_layer(self):
        self.layer.public = True
        response = self.client.storage.update_layer(self.layer)
        self.assertEquals(response, {'status': 'OK'})
        response = self.client.storage.get_layer(self.layer.name)
        self.assertEquals(response['name'], self.layer.name)
        self.assertEquals(response['title'], self.layer.title)
        self.assertEquals(response['description'], self.layer.description)
        self.assertEquals(response['callback_urls'], self.layer.callback_urls)
        self.assertEquals(response['public'], self.layer.public)
        self.assert_(response['created'])
        self.assert_(response['updated'])

    def test_get_layers(self):
        response = self.client.storage.get_layers()
        self.assert_(len(response.get('layers')) >= 1)


    # Utility functions

    def assertPointIsRecord(self, point, record):
        self.assertEquals(point['type'], 'Feature')
        self.assertEquals(point['id'], record.id)
        self.assertEquals(point['layerLink']['href'],
                          'http://api.simplegeo.com/0.1/layer/%s.json'
                            % record.layer)
        self.assertEquals(point['selfLink']['href'],
                          'http://api.simplegeo.com/0.1/records/%s/%s.json'
                            % (record.layer, record.id))
        self.assertEquals(point['created'], record.created)
        self.assertEquals(point['geometry']['type'], 'Point')
        self.assertEquals(point['geometry']['coordinates'][0], D(record.lon))
        self.assertEquals(point['geometry']['coordinates'][1], D(record.lat))

    def addRecordAndSleep(self, record):
        self.client.storage.add_record(record)
        self.created_records.append(record)
        time.sleep(5)

    def addRecordsAndSleep(self, layer, records):
        self.client.storage.add_records(layer, records)
        self.created_records += records
        time.sleep(5)

    def assertAddressEquals(self, record):
        self.assertEquals(record.get('properties').get('state_name'), 'California')
        self.assertEquals(record.get('properties').get('street_number'), '4176')
        self.assertEquals(record.get('properties').get('country'), 'US')
        self.assertEquals(record.get('properties').get('street'), '26th St')
        self.assertEquals(record.get('properties').get('postal_code'), '94131')
        self.assertEquals(record.get('properties').get('county_name'), 'San Francisco')
        self.assertEquals(record.get('properties').get('county_code'), '075')
        self.assertEquals(record.get('properties').get('state_code'), 'CA')
        self.assertEquals(record.get('properties').get('place_name'), 'San Francisco')

    def assertOverlapEquals(self, record):
        self.assertEquals(record.get('name'), '06075021500')
        self.assertEquals(record.get('type'), 'Census Tract')
        self.assertEquals(record.get('bounds')[0], -122.431477)
        self.assertEquals(record.get('bounds')[1], 37.741833)
        self.assertEquals(record.get('bounds')[2], -122.421328)
        self.assertEquals(record.get('bounds')[3], 37.748123999999997)
        self.assertEquals(record.get('abbr'), '')
        self.assertEquals(record.get('id'), 'Census_Tract:06075021500:9q8ywp')

    def assertCorrectCoordinates(self, coordinate_list):
        self.assertEquals(coordinate_list[0][0], 37.748046875)
        self.assertEquals(coordinate_list[0][1], -122.43359375)
        self.assertEquals(coordinate_list[1][0], 37.7490234375)
        self.assertEquals(coordinate_list[1][1], -122.43359375)
        self.assertEquals(coordinate_list[2][0], 37.7490234375)
        self.assertEquals(coordinate_list[2][1], -122.4326171875)
        self.assertEquals(coordinate_list[3][0], 37.748046875)
        self.assertEquals(coordinate_list[3][1], -122.4326171875)
        self.assertEquals(coordinate_list[4][0], 37.748046875)
        self.assertEquals(coordinate_list[4][1], -122.43359375)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = google
import urllib
from urllib2 import urlopen

def get_translated_address_from_feature(feature, translate_to='ru'):
    """Return a translated address using Google Translate API.
    See http://goo.gl/HXJvu for list of language codes."""
    feature = feature.to_dict()
    address = feature['properties']['address']
    langpair = '%s|%s'%('en',translate_to)
    base_url = 'http://ajax.googleapis.com/ajax/services/language/translate?'
    params = urllib.urlencode( (('v',1.0),
                                ('q',address),
                                ('langpair',langpair),) )
    url = base_url+params
    content = urlopen(url).read()
    start_idx = content.find('"translatedText":"')+18
    translation = content[start_idx:]
    end_idx = translation.find('"}, "')
    translation = translation[:end_idx]
    return translation

########NEW FILE########
__FILENAME__ = json
# -*- coding: utf-8 -*-
#
# © 2011 SimpleGeo, Inc All rights reserved.
# Author: Ian Eure <ian@simplegeo.com>
#

"""JSON helper."""

from functools import partial

import simplejson

loads = partial(simplejson.loads, use_decimal=True)
load = partial(simplejson.load, use_decimal=True)
dumps = partial(simplejson.dumps, use_decimal=True)
dump = partial(simplejson.dump, use_decimal=True)

########NEW FILE########
__FILENAME__ = models
import time
import copy
import simplegeo.json as json
from util import json_decode, deep_swap, deep_validate_lat_lon, is_simplegeohandle, SIMPLEGEOHANDLE_RSTR

class Feature:
    def __init__(self, coordinates, geomtype='Point', simplegeohandle=None, properties=None, strict_lon_validation=False):
        """
        The simplegeohandle and the record_id are both optional -- you
        can have one or the other or both or neither.

        A simplegeohandle is globally unique and is assigned by the
        Places service. It is returned from the Places service in the
        response to a request to add a place to the Places database
        (the add_feature method).

        The simplegeohandle is passed in as an argument to the
        constructor, named "simplegeohandle", and is stored in the
        "id" attribute of the Feature instance.

        A record_id is scoped to your particular user account and is
        chosen by you. The only use for the record_id is in case you
        call add_feature and you have already previously added that
        feature to the database -- if there is already a feature from
        your user account with the same record_id then the Places
        service will return that feature to you, along with that
        feature's simplegeohandle, instead of making a second, duplicate
        feature.

        A record_id is passed in as a value in the properties dict
        named "record_id".

        geomtype is a GeoJSON geometry type such as "Point",
        "Polygon", or "Multipolygon". coordinates is a GeoJSON
        coordinates *except* that each lat/lon pair is written in
        order lat, lon instead of the GeoJSON order of lon, at.

        When a Feature is being submitted to the SimpleGeo Places
        database, if there is a key 'private' in the properties dict
        which is set to True, then the Feature is intended to be
        visible only to your user account. If there is no 'private'
        key or if there is a 'private' key which is set to False, then
        the Feature is intended to be merged into the publicly visible
        Places Database.

        Note that even if it is intended to be merged into the public
        Places Database the actual process of merging it into the
        public shared database may take some time, and the newly added
        Feature will be visible to your account right away even if it
        isn't (yet) visible to the public.

        For the meaning of strict_lon_validation, please see the
        function is_valid_lon().
        """
        try:
            deep_validate_lat_lon(coordinates, strict_lon_validation=strict_lon_validation)
        except ValueError, le:
            raise TypeError("The first argument, 'coordinates' is required to be a 2-element sequence of lon, lat for a point (or a more complicated set of coordinates for polygons or multipolygons), but it was %s :: %r. The error that was raised from validating this was: %s" % (type(coordinates), coordinates, le))

        if not (simplegeohandle is None or is_simplegeohandle(simplegeohandle)):
            raise TypeError("The third argument, 'simplegeohandle' is required to be None or to match this regex: %s, but it was %s :: %r" % (SIMPLEGEOHANDLE_RSTR, type(simplegeohandle), simplegeohandle))

        record_id = properties and properties.get('record_id') or None
        if not (record_id is None or isinstance(record_id, basestring)):
            raise TypeError("record_id is required to be None or a string, but it was: %r :: %s." % (type(record_id), record_id))
        self.strict_lon_validation = strict_lon_validation
        if not coordinates:
            raise ValueError("Coordinates may not be empty.")
        if simplegeohandle is not None:
            self.id = simplegeohandle
        self.coordinates = coordinates
        self.geomtype = geomtype
        self.properties = {'private': False}
        if properties:
            self.properties.update(properties)

    @classmethod
    def from_dict(cls, data, strict_lon_validation=False):
        """
        data is a GeoJSON standard data structure, including that the
        coordinates are in GeoJSON order (lon, lat) instead of
        SimpleGeo order (lat, lon)
        """
        assert isinstance(data, dict), (type(data), repr(data))
        coordinates = deep_swap(data['geometry']['coordinates'])
        try:
            deep_validate_lat_lon(coordinates, strict_lon_validation=strict_lon_validation)
        except TypeError, le:
            raise TypeError("The 'coordinates' value is required to be a 2-element sequence of lon, lat for a point (or a more complicated set of coordinates for polygons or multipolygons), but it was %s :: %r. The error that was raised from validating this was: %s" % (type(coordinates), coordinates, le))
        feature = cls(
            simplegeohandle = data.get('id'),
            coordinates = coordinates,
            geomtype = data['geometry']['type'],
            properties = data.get('properties')
            )

        return feature

    def to_dict(self):
        """
        Returns a GeoJSON object, including having its coordinates in
        GeoJSON standad order (lon, lat) instead of SimpleGeo standard
        order (lat, lon).
        """
        d = {
            'type': 'Feature',
            'geometry': {
                'type': self.geomtype,
                'coordinates': deep_swap(self.coordinates)
            },
            'properties': copy.deepcopy(self.properties),
        }

        if hasattr(self, 'id'):
            d['id'] = self.id
        
        return d

    @classmethod
    def from_json(cls, jsonstr):
        return cls.from_dict(json_decode(jsonstr))

    def to_json(self):
        return json.dumps(self.to_dict())


class Record(object):
    def __init__(self, layer, id, lat, lon, created=None, **kwargs):
        self.layer = layer
        self.id = id
        self.lon = lon
        self.lat = lat
        if created is None:
            self.created = int(time.time())
        else:
            self.created = created
        self.__dict__.update(kwargs)

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
        coord = data['geometry']['coordinates']
        record = cls(data['properties']['layer'], data['id'], lat=coord[1], lon=coord[0])
        record.created = data.get('created', record.created)
        record.__dict__.update(dict((k, v) for k, v in data['properties'].iteritems()
                                    if k not in ('layer', 'created')))
        return record

    def to_dict(self):
        return {
            'type': 'Feature',
            'id': self.id,
            'created': self.created,
            'geometry': {
                'type': 'Point',
                'coordinates': [self.lon, self.lat],
            },
            'properties': dict((k, v) for k, v in self.__dict__.iteritems()
                                        if k not in ('lon', 'lat', 'id', 'created')),
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def __str__(self):
        return self.to_json()

    def __repr__(self):
        return "Record(layer=%s, id=%s, lat=%s, lon=%s)" % (self.layer, self.id, self.lat, self.lon)

    def __hash__(self):
        return hash((self.layer, self.id))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id == other.id

class Layer(object):
    def __init__(self, name, title='', description='', public=False,
                 callback_urls=[]):
        self.name = name
        self.title = title
        self.description = description
        self.public = public
        self.callback_urls = callback_urls

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
        layer = cls(data.get('name'), data.get('title'),
                    data.get('description'), data.get('public'),
                    data.get('callback_urls', []))
        return layer

    def to_dict(self):
        return {
            'name': self.name,
            'title': self.title,
            'description': self.description,
            'public': self.public,
            'callback_urls': self.callback_urls,
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def __str__(self):
        return self.to_json()

    def __repr__(self):
        return "Layer(name=%s, public=%s)" % (self.name, self.public)

    def __hash__(self):
        return hash((self.name))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.name == other.name

########NEW FILE########
__FILENAME__ = places_10
# -*- coding: utf-8 -*-
#
# © 2011 SimplegGeo, Inc. All rights reserved.
# Author: Ian Eure <ian@simplegeo.com>
#

"""Places 1.0 client."""

from simplegeo.util import (json_decode, APIError, SIMPLEGEOHANDLE_RSTR,
                            is_valid_lat, is_valid_lon,
                            _assert_valid_lat, _assert_valid_lon,
                            is_valid_ip, is_numeric, is_simplegeohandle)
from simplegeo import Client as ParentClient
from simplegeo.models import Feature

class Client(ParentClient):

    def __init__(self, key, secret, api_version='1.0', **kwargs):
        ParentClient.__init__(self, key, secret, **kwargs)

        places_endpoints = [
            ['create', '/places'],
            ['search', '/places/%(lat)s,%(lon)s.json'],
            ['search_by_ip', '/places/%(ipaddr)s.json'],
            ['search_by_my_ip', '/places/ip.json'],
            ['search_by_address', '/places/address.json']
        ]

        self.endpoints.update(map(lambda x: (x[0], api_version+x[1]), places_endpoints))

    def add_feature(self, feature):
        """Create a new feature, returns the simplegeohandle. """
        endpoint = self._endpoint('create')
        if hasattr(feature, 'id'):
            # only simplegeohandles or None should be stored in self.id
            assert is_simplegeohandle(feature.id)
            raise ValueError('A feature cannot be added to the Places database when it already has a simplegeohandle: %s' % (feature.id,))
        jsonrec = feature.to_json()
        resp, content = self._request(endpoint, "POST", jsonrec)
        if resp['status'] != "202":
            raise APIError(int(resp['status']), content, resp)
        contentobj = json_decode(content)
        if not contentobj.has_key('id'):
            raise APIError(int(resp['status']), content, resp)
        handle = contentobj['id']
        assert is_simplegeohandle(handle)
        return handle

    def update_feature(self, feature):
        """Update a Places feature."""
        endpoint = self._endpoint('feature', simplegeohandle=feature.id)
        return self._request(endpoint, 'POST', feature.to_json())[1]

    def delete_feature(self, simplegeohandle):
        """Delete a Places feature."""
        if not is_simplegeohandle(simplegeohandle):
            raise ValueError("simplegeohandle is required to match "
                             "the regex %s" % SIMPLEGEOHANDLE_RSTR)
        endpoint = self._endpoint('feature', simplegeohandle=simplegeohandle)
        return self._request(endpoint, 'DELETE')[1]

    def search(self, lat, lon, radius=None, query=None, category=None, num=None):
        """Search for places near a lat/lon, within a radius (in kilometers)."""
        _assert_valid_lat(lat)
        _assert_valid_lon(lon)
        if (radius and not is_numeric(radius)):
            raise ValueError("Radius must be numeric.")
        if (query and not isinstance(query, basestring)):
            raise ValueError("Query must be a string.")
        if (category and not isinstance(category, basestring)):
            raise ValueError("Category must be a string.")
        if (num and not is_numeric(num)):
            raise ValueError("Num parameter must be numeric.")

        if isinstance(query, unicode):
            query = query.encode('utf-8')
        if isinstance(category, unicode):
            category = category.encode('utf-8')

        kwargs = { }
        if radius:
            kwargs['radius'] = radius
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        if num:
            kwargs['num'] = num

        endpoint = self._endpoint('search', lat=lat, lon=lon)

        result = self._request(endpoint, 'GET', data=kwargs)[1]

        fc = json_decode(result)
        return [Feature.from_dict(f) for f in fc['features']]

    def search_by_ip(self, ipaddr, radius=None, query=None, category=None, num=None):
        """
        Search for places near an IP address, within a radius (in
        kilometers).

        The server uses guesses the latitude and longitude from the
        ipaddr and then does the same thing as search(), using that
        guessed latitude and longitude.
        """
        if not is_valid_ip(ipaddr):
            raise ValueError("Address %s is not a valid IP" % ipaddr)
        if (radius and not is_numeric(radius)):
            raise ValueError("Radius must be numeric.")
        if (query and not isinstance(query, basestring)):
            raise ValueError("Query must be a string.")
        if (category and not isinstance(category, basestring)):
            raise ValueError("Category must be a string.")
        if (num and not is_numeric(num)):
            raise ValueError("Num parameter must be numeric.")

        if isinstance(query, unicode):
            query = query.encode('utf-8')
        if isinstance(category, unicode):
            category = category.encode('utf-8')

        kwargs = { }
        if radius:
            kwargs['radius'] = radius
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        if num:
            kwargs['num'] = num

        endpoint = self._endpoint('search_by_ip', ipaddr=ipaddr)

        result = self._request(endpoint, 'GET', data=kwargs)[1]

        fc = json_decode(result)
        return [Feature.from_dict(f) for f in fc['features']]

    def search_by_my_ip(self, radius=None, query=None, category=None, num=None):
        """
        Search for places near your IP address, within a radius (in
        kilometers).

        The server gets the IP address from the HTTP connection (this
        may be the IP address of your device or of a firewall, NAT, or
        HTTP proxy device between you and the server), and then does
        the same thing as search_by_ip(), using that IP address.
        """
        if (radius and not is_numeric(radius)):
            raise ValueError("Radius must be numeric.")
        if (query and not isinstance(query, basestring)):
            raise ValueError("Query must be a string.")
        if (category and not isinstance(category, basestring)):
            raise ValueError("Category must be a string.")
        if (num and not is_numeric(num)):
            raise ValueError("Num parameter must be numeric.")

        if isinstance(query, unicode):
            query = query.encode('utf-8')
        if isinstance(category, unicode):
            category = category.encode('utf-8')

        kwargs = { }
        if radius:
            kwargs['radius'] = radius
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        if num:
            kwargs['num'] = num

        endpoint = self._endpoint('search_by_my_ip')

        result = self._request(endpoint, 'GET', data=kwargs)[1]

        fc = json_decode(result)
        return [Feature.from_dict(f) for f in fc['features']]

    def search_by_address(self, address, radius=None, query=None, category=None, num=None):
        """
        Search for places near the given address, within a radius (in
        kilometers).

        The server figures out the latitude and longitude from the
        street address and then does the same thing as search(), using
        that deduced latitude and longitude.
        """
        if not isinstance(address, basestring) or not address.strip():
            raise ValueError("Address must be a non-empty string.")
        if (radius and not is_numeric(radius)):
            raise ValueError("Radius must be numeric.")
        if (query and not isinstance(query, basestring)):
            raise ValueError("Query must be a string.")
        if (category and not isinstance(category, basestring)):
            raise ValueError("Category must be a string.")
        if (num and not is_numeric(num)):
            raise ValueError("Num parameter must be numeric.")

        if isinstance(address, unicode):
            address = address.encode('utf-8')
        if isinstance(query, unicode):
            query = query.encode('utf-8')
        if isinstance(category, unicode):
            category = category.encode('utf-8')

        kwargs = { 'address': address }
        if radius:
            kwargs['radius'] = radius
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        if num:
            kwargs['num'] = num

        endpoint = self._endpoint('search_by_address')

        result = self._request(endpoint, 'GET', data=kwargs)[1]

        fc = json_decode(result)
        return [Feature.from_dict(f) for f in fc['features']]

########NEW FILE########
__FILENAME__ = places_12
# -*- coding: utf-8 -*-
#
# © 2011 SimplegGeo, Inc. All rights reserved.
# Author: Ian Eure <ian@simplegeo.com>
#

"""Places 1.2 client."""

import simplejson as json

from simplegeo.util import (json_decode, APIError, DecodeError,
                            SIMPLEGEOHANDLE_RSTR, is_valid_lat, is_valid_lon,
                            _assert_valid_lat, _assert_valid_lon,
                            is_valid_ip, is_numeric, is_simplegeohandle)
from simplegeo import Client as ParentClient


class Response(dict):

    """A response object which encapsulates headers & body."""

    def __init__(self, body, headers):
        try:
            body = json_decode(body)
        except DecodeError:
            body = {}
        dict.__init__(self, body)
        self.headers = headers


class Client(ParentClient):

    def __init__(self, key, secret, **kwargs):
        ParentClient.__init__(self, key, secret, **kwargs)

        self.endpoints.update(
            feature='1.2/places/%(place_id)s.json',
            search='1.2/places/%(lat)s,%(lon)s.json',
            search_text='1.2/places/search.json',
            search_bbox='1.2/places/%(lat_sw)s,%(lon_sw)s,%(lat_ne)s,%(lon_ne)s.json',
            search_by_ip='1.2/places/%(ipaddr)s.json',
            search_by_my_ip='1.2/places/ip.json',
            search_by_address='1.2/places/address.json')

    def _respond(self, headers, response):
        """Return the correct structure for this response."""
        return Response(response, headers)

    def get_feature(self, place_id):
        """Return the GeoJSON representation of a feature."""
        (headers, response) = self._request(
            self._endpoint('feature', place_id=place_id), 'GET')
        return self._respond(headers, response)

    def search(self, lat, lon, radius=None, query=None, category=None,
               limit=None, start=None):
        """Search for places near a lat/lon, within a radius (in kilometers)."""
        _assert_valid_lat(lat)
        _assert_valid_lon(lon)
        if (radius and not is_numeric(radius)):
            raise ValueError("Radius must be numeric.")
        if (query and not isinstance(query, basestring)):
            raise ValueError("Query must be a string.")
        if (category and not isinstance(category, basestring)):
            raise ValueError("Category must be a string.")
        if (limit and not is_numeric(limit)):
            raise ValueError("Limit parameter must be numeric.")
        if (start and not is_numeric(start)):
            raise ValueError("Start parameter must be numeric.")

        if isinstance(query, unicode):
            query = query.encode('utf-8')
        if isinstance(category, unicode):
            category = category.encode('utf-8')

        kwargs = { }
        if radius:
            kwargs['radius'] = radius
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        if limit:
            kwargs['limit'] = limit
        if start:
            kwargs['start'] = start

        return self._respond(*self._request(self._endpoint(
                    'search', lat=lat, lon=lon),
                              'GET', data=kwargs))

    def search_text(self, query=None, category=None, limit=None, start=None):
        """Fulltext search for places."""
        if (query and not isinstance(query, basestring)):
            raise ValueError("Query must be a string.")
        if (category and not isinstance(category, basestring)):
            raise ValueError("Category must be a string.")
        if (limit and not is_numeric(limit)):
            raise ValueError("Limit parameter must be numeric.")
        if (start and not is_numeric(start)):
            raise ValueError("Start parameter must be numeric.")

        if isinstance(query, unicode):
            query = query.encode('utf-8')
        if isinstance(category, unicode):
            category = category.encode('utf-8')

        kwargs = { }
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        if limit:
            kwargs['limit'] = limit
        if start:
            kwargs['start'] = start

        return self._respond(*self._request(self._endpoint('search_text'),
                                            'GET', data=kwargs))

    def search_bbox(self, lat_sw, lon_sw, lat_ne, lon_ne, query=None,
                    category=None, limit=None, start=None):
        """Return places inside a box of (lat_sw, lon_sw), (lat_ne, lon_ne)."""
        _assert_valid_lat(lat_sw)
        _assert_valid_lat(lat_ne)
        _assert_valid_lon(lon_sw)
        _assert_valid_lon(lon_ne)
        if (query and not isinstance(query, basestring)):
            raise ValueError("Query must be a string.")
        if (category and not isinstance(category, basestring)):
            raise ValueError("Category must be a string.")
        if (limit and not is_numeric(limit)):
            raise ValueError("Limit parameter must be numeric.")
        if (start and not is_numeric(start)):
            raise ValueError("Start parameter must be numeric.")

        if isinstance(query, unicode):
            query = query.encode('utf-8')
        if isinstance(category, unicode):
            category = category.encode('utf-8')

        kwargs = { }
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        if limit:
            kwargs['limit'] = limit
        if start:
            kwargs['start'] = start

        return self._respond(*self._request(self._endpoint(
                    'search_bbox', lat_sw=lat_sw, lon_sw=lon_sw,
                    lat_ne=lat_ne, lon_ne=lon_ne), 'GET', data=kwargs))

    def search_by_ip(self, ipaddr, radius=None, query=None,
                     category=None, limit=None, start=None):
        """
        Search for places near an IP address, within a radius (in
        kilometers).

        The server uses guesses the latitude and longitude from the
        ipaddr and then does the same thing as search(), using that
        guessed latitude and longitude.
        """
        if not is_valid_ip(ipaddr):
            raise ValueError("Address %s is not a valid IP" % ipaddr)
        if (radius and not is_numeric(radius)):
            raise ValueError("Radius must be numeric.")
        if (query and not isinstance(query, basestring)):
            raise ValueError("Query must be a string.")
        if (category and not isinstance(category, basestring)):
            raise ValueError("Category must be a string.")
        if (limit and not is_numeric(limit)):
            raise ValueError("Limit parameter must be numeric.")
        if (start and not is_numeric(start)):
            raise ValueError("Start parameter must be numeric.")

        if isinstance(query, unicode):
            query = query.encode('utf-8')
        if isinstance(category, unicode):
            category = category.encode('utf-8')

        kwargs = { }
        if radius:
            kwargs['radius'] = radius
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        if limit:
            kwargs['limit'] = limit
        if start:
            kwargs['start'] = start

        return self._respond(*self._request(self._endpoint(
                    'search_by_ip', ipaddr=ipaddr), 'GET', data=kwargs))

    def search_by_my_ip(self, radius=None, query=None, category=None,
                        limit=None, start=None):
        """
        Search for places near your IP address, within a radius (in
        kilometers).

        The server gets the IP address from the HTTP connection (this
        may be the IP address of your device or of a firewall, NAT, or
        HTTP proxy device between you and the server), and then does
        the same thing as search_by_ip(), using that IP address.
        """
        if (radius and not is_numeric(radius)):
            raise ValueError("Radius must be numeric.")
        if (query and not isinstance(query, basestring)):
            raise ValueError("Query must be a string.")
        if (category and not isinstance(category, basestring)):
            raise ValueError("Category must be a string.")
        if (limit and not is_numeric(limit)):
            raise ValueError("Limit parameter must be numeric.")
        if (start and not is_numeric(start)):
            raise ValueError("Start parameter must be numeric.")

        if isinstance(query, unicode):
            query = query.encode('utf-8')
        if isinstance(category, unicode):
            category = category.encode('utf-8')

        kwargs = { }
        if radius:
            kwargs['radius'] = radius
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        if limit:
            kwargs['limit'] = limit
        if start:
            kwargs['start'] = start

        return self._respond(*self._request(self._endpoint(
                    'search_by_my_ip'), 'GET', data=kwargs))

    def search_by_address(self, address, radius=None, query=None,
                          category=None, limit=None, start=None):
        """
        Search for places near the given address, within a radius (in
        kilometers).

        The server figures out the latitude and longitude from the
        street address and then does the same thing as search(), using
        that deduced latitude and longitude.
        """
        if not isinstance(address, basestring) or not address.strip():
            raise ValueError("Address must be a non-empty string.")
        if (radius and not is_numeric(radius)):
            raise ValueError("Radius must be numeric.")
        if (query and not isinstance(query, basestring)):
            raise ValueError("Query must be a string.")
        if (category and not isinstance(category, basestring)):
            raise ValueError("Category must be a string.")
        if (limit and not is_numeric(limit)):
            raise ValueError("Limit parameter must be numeric.")

        if isinstance(address, unicode):
            address = address.encode('utf-8')
        if isinstance(query, unicode):
            query = query.encode('utf-8')
        if isinstance(category, unicode):
            category = category.encode('utf-8')
        if (start and not is_numeric(start)):
            raise ValueError("Start parameter must be numeric.")

        kwargs = { 'address': address }
        if radius:
            kwargs['radius'] = radius
        if query:
            kwargs['q'] = query
        if category:
            kwargs['category'] = category
        if limit:
            kwargs['limit'] = limit
        if start:
            kwargs['start'] = start

        return self._respond(*self._request(self._endpoint(
                    'search_by_address'), 'GET', data=kwargs))

########NEW FILE########
__FILENAME__ = test_client
import unittest
from decimal import Decimal as D

import simplegeo.json as json
import mock

from simplegeo import Client
from simplegeo.models import Feature
from simplegeo.util import APIError, DecodeError, is_valid_lat, is_valid_lon, is_valid_ip, to_unicode

MY_OAUTH_KEY = 'MY_OAUTH_KEY'
MY_OAUTH_SECRET = 'MY_SECRET_KEY'
TESTING_LAYER = 'TESTING_LAYER'

API_VERSION = '1.0'
API_HOST = 'api.simplegeo.com'
API_PORT = 80

class ReallyEqualMixin:
    def failUnlessReallyEqual(self, a, b, msg='', *args, **kwargs):
        self.failUnlessEqual(a, b, msg, *args, **kwargs)
        self.failUnlessEqual(type(a), type(b), msg="a :: %r, b :: %r, %r" % (a, b, msg), *args, **kwargs)

class ToUnicodeTest(unittest.TestCase, ReallyEqualMixin):
    def test_to_unicode(self):
        self.failUnlessReallyEqual(to_unicode('x'), u'x')
        self.failUnlessReallyEqual(to_unicode(u'x'), u'x')
        self.failUnlessReallyEqual(to_unicode('\xe2\x9d\xa4'), u'\u2764')

class LatLonValidationTest(unittest.TestCase):

    def test_is_valid_lon(self):
        self.failUnless(is_valid_lon(180, strict=True))
        self.failUnless(is_valid_lon(180.0, strict=True))
        self.failUnless(is_valid_lon(D('180.0'), strict=True))
        self.failUnless(is_valid_lon(-180, strict=True))
        self.failUnless(is_valid_lon(-180.0, strict=True))
        self.failUnless(is_valid_lon(D('-180.0'), strict=True))

        self.failIf(is_valid_lon(180.0002, strict=True))
        self.failIf(is_valid_lon(D('180.0002'), strict=True))
        self.failIf(is_valid_lon(-180.0002, strict=True))
        self.failIf(is_valid_lon(D('-180.0002'), strict=True))

        self.failUnless(is_valid_lon(180.0002, strict=False))
        self.failUnless(is_valid_lon(D('180.0002'), strict=False))
        self.failUnless(is_valid_lon(-180.0002, strict=False))
        self.failUnless(is_valid_lon(D('-180.0002'), strict=False))

        self.failIf(is_valid_lon(360.0002, strict=False))
        self.failIf(is_valid_lon(D('360.0002'), strict=False))
        self.failIf(is_valid_lon(-360.0002, strict=False))
        self.failIf(is_valid_lon(D('-360.0002'), strict=False))

    def test_is_valid_lat(self):
        self.failUnless(is_valid_lat(90))
        self.failUnless(is_valid_lat(90.0))
        self.failUnless(is_valid_lat(D('90.0')))
        self.failUnless(is_valid_lat(-90))
        self.failUnless(is_valid_lat(-90.0))
        self.failUnless(is_valid_lat(D('-90.0')))

        self.failIf(is_valid_lat(90.0002))
        self.failIf(is_valid_lat(D('90.0002')))
        self.failIf(is_valid_lat(-90.0002))
        self.failIf(is_valid_lat(D('-90.0002')))

class DecodeErrorTest(unittest.TestCase):
    def test_repr(self):
        body = 'this is not json'
        try:
            json.loads('this is not json')
        except ValueError, le:
            e = DecodeError(body, le)
        else:
            self.fail("We were supposed to get an exception from json.loads().")

        self.failUnless("Could not decode JSON" in e.msg, repr(e.msg))
        self.failUnless('JSONDecodeError' in repr(e), repr(e))

class ClientTest(unittest.TestCase):
    def setUp(self):
        self.client = Client(MY_OAUTH_KEY, MY_OAUTH_SECRET, host=API_HOST, port=API_PORT)
        self.query_lat = D('37.8016')
        self.query_lon = D('-122.4783')

    def test_is_valid_ip(self):
        self.failUnless(is_valid_ip('192.0.32.10'))
        self.failIf(is_valid_ip('i am not an ip address at all'))

    def test_wrong_endpoint(self):
        self.assertRaises(Exception, self.client._endpoint, 'wrongwrong')

    def test_missing_argument(self):
        self.assertRaises(Exception, self.client._endpoint, 'feature')

    def test_get_feature_useful_validation_error_message(self):
        c = Client('whatever', 'whatever')
        try:
            c.get_feature('wrong thing')
        except TypeError, e:
            self.failUnless(str(e).startswith('simplegeohandle is required to match '), str(e))
        else:
            self.fail('Should have raised exception.')

    def test_get_most_recent_http_headers(self):
        h = self.client.get_most_recent_http_headers()
        self.failUnlessEqual(h, {})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', 'thingie': "just to see if you're listening"}, EXAMPLE_POINT_BODY)
        self.client.http = mockhttp

        self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        h = self.client.get_most_recent_http_headers()
        self.failUnlessEqual(h, {'status': '200', 'content-type': 'application/json', 'thingie': "just to see if you're listening"})

    def test_get_point_feature(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', 'thingie': "just to see if you're listening"}, EXAMPLE_POINT_BODY)
        self.client.http = mockhttp

        res = self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')
        # the code under test is required to have json-decoded this before handing it back
        self.failUnless(isinstance(res, Feature), (repr(res), type(res)))

    def test_get_polygon_feature(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.http = mockhttp

        res = self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))

        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')
        # the code under test is required to have json-decoded this before handing it back
        self.failUnless(isinstance(res, Feature), (repr(res), type(res)))

    def test_get_feature_bad_json(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY + 'some crap')
        self.client.http = mockhttp

        try:
            self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        except DecodeError, e:
            self.failUnlessEqual(e.code, None, repr(e.code))

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_dont_json_decode_results(self):
        """ _request() is required to return the exact string that the HTTP
        server sent to it -- no transforming it, such as by json-decoding. """

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, '{ "Hello": "I am a string. \xe2\x9d\xa4" }'.decode('utf-8'))
        self.client.http = mockhttp
        res = self.client._request("http://thing", 'POST')[1]
        self.failUnlessEqual(res, '{ "Hello": "I am a string. \xe2\x9d\xa4" }'.decode('utf-8'))

    def test_dont_Recordify_results(self):
        """ _request() is required to return the exact string that the HTTP
        server sent to it -- no transforming it, such as by json-decoding and
        then constructing a Record. """

        EXAMPLE_RECORD_JSONSTR=json.dumps({ 'geometry' : { 'type' : 'Point', 'coordinates' : [D('10.0'), D('11.0')] }, 'id' : 'my_id', 'type' : 'Feature', 'properties' : { 'key' : 'value'  , 'type' : 'object' } })

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_RECORD_JSONSTR)
        self.client.http = mockhttp
        res = self.client._request("http://thing", 'POST')[1]
        self.failUnlessEqual(res, EXAMPLE_RECORD_JSONSTR)

    def test_get_feature_error(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '500', 'content-type': 'application/json', }, '{"message": "help my web server is confuzzled"}')
        self.client.http = mockhttp

        try:
            self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        except APIError, e:
            self.failUnlessEqual(e.code, 500, repr(e.code))
            self.failUnlessEqual(e.msg, '{"message": "help my web server is confuzzled"}', (type(e.msg), repr(e.msg)))

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_APIError(self):
        e = APIError(500, 'whee', {'status': "500"})
        self.failUnlessEqual(e.code, 500)
        self.failUnlessEqual(e.msg, 'whee')
        repr(e)
        str(e)

EXAMPLE_POINT_BODY="""
{"geometry":{"type":"Point","coordinates":[-105.048054,40.005274]},"type":"Feature","id":"SG_6sRJczWZHdzNj4qSeRzpzz_40.005274_-105.048054@1291669259","properties":{"province":"CO","city":"Erie","name":"CMD Colorado Inc","tags":["sandwich"],"country":"US","phone":"+1 303 664 9448","address":"305 Baron Ct","owner":"simplegeo","classifiers":[{"category":"Restaurants","type":"Food & Drink","subcategory":""}],"postcode":"80516"}}
"""

EXAMPLE_BODY="""
{"geometry":{"type":"Polygon","coordinates":[[[-86.3672637,33.4041157],[-86.3676356,33.4039745],[-86.3681259,33.40365],[-86.3685992,33.4034242],[-86.3690556,33.4031137],[-86.3695121,33.4027609],[-86.3700361,33.4024363],[-86.3705601,33.4021258],[-86.3710166,33.4018012],[-86.3715575,33.4014061],[-86.3720647,33.4008557],[-86.3724366,33.4005311],[-86.3730621,33.3998395],[-86.3733156,33.3992891],[-86.3735523,33.3987811],[-86.3737383,33.3983153],[-86.3739073,33.3978355],[-86.374144,33.3971016],[-86.3741609,33.3968758],[-86.3733494,33.3976943],[-86.3729606,33.3980189],[-86.3725211,33.3984141],[-86.3718111,33.3990069],[-86.3713378,33.399402],[-86.370949,33.3997266],[-86.3705094,33.3999948],[-86.3701206,33.4003899],[-86.3697487,33.4007287],[-86.369157,33.4012791],[-86.3687682,33.401646],[-86.3684132,33.4019847],[-86.368092,33.4023798],[-86.3676694,33.4028738],[-86.3674835,33.4033113],[-86.3672975,33.4037487],[-86.3672637,33.4041157],[-86.3672637,33.4041157]]]},"type":"Feature","properties":{"category":"Island","license":"http://creativecommons.org/licenses/by-sa/2.0/","handle":"SG_4b10i9vCyPnKAYiYBLKZN7_33.400800_-86.370802","subcategory":"","name":"Elliott Island","attribution":"(c) OpenStreetMap (http://openstreetmap.org/) and contributors CC-BY-SA (http://creativecommons.org/licenses/by-sa/2.0/)","type":"Physical Feature","abbr":""},"id":"SG_4b10i9vCyPnKAYiYBLKZN7"}
"""

class TestAnnotations(unittest.TestCase):

    def setUp(self):
        self.client = Client(MY_OAUTH_KEY, MY_OAUTH_SECRET, host=API_HOST, port=API_PORT)
        self.handle = 'SG_4H2GqJDZrc0ZAjKGR8qM4D'

    def test_get_annotations(self):
        mockhttp = mock.Mock()
        headers = {'status': '200', 'content-type': 'application/json'}
        mockhttp.request.return_value = (headers, json.dumps(EXAMPLE_ANNOTATIONS_RESPONSE))
        self.client.http = mockhttp

        res = self.client.get_annotations(self.handle)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s/annotations.json' % (API_VERSION, self.handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

        # Make sure client returns a dict.
        self.failUnless(isinstance(res, dict))

    def test_get_annotations_bad_handle(self):
        try:
            self.client.get_annotations('bad_handle')
        except TypeError, e:
            self.failUnless(str(e).startswith('simplegeohandle is required to match the regex'))
        else:
            self.fail('Should have raised exception.')

    def test_annotate(self):
        mockhttp = mock.Mock()
        headers = {'status': '200', 'content-type': 'application/json'}
        mockhttp.request.return_value = (headers, json.dumps(EXAMPLE_ANNOTATE_RESPONSE))
        self.client.http = mockhttp

        res = self.client.annotate(self.handle, EXAMPLE_ANNOTATIONS, True)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s/annotations.json' % (API_VERSION, self.handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'POST')

        # Make sure client returns a dict.
        self.failUnless(isinstance(res, dict))

    def test_annotate_bad_annotations_type(self):
        annotations = 'not_a_dict'
        try:
            self.client.annotate(self.handle, annotations, True)
        except TypeError, e:
            self.failUnless(str(e) == 'annotations must be of type dict')
        else:
            self.fail('Should have raised exception.')

    def test_annotate_empty_annotations_dict(self):
        annotations = {}
        try:
            self.client.annotate(self.handle, annotations, True)
        except ValueError, e:
            self.failUnless(str(e) == 'annotations dict is empty')
        else:
            self.fail('Should have raised exception.')

    def test_annotate_empty_annotation_type_dict(self):
        annotations = {
            'annotation_type_1': {
                'foo': 'bar'},
            'annotation_type_2': {
                }
            }
        try:
            self.client.annotate(self.handle, annotations, True)
        except ValueError, e:
            self.failUnless(str(e) == 'annotation type "annotation_type_2" is empty')
        else:
            self.fail('Should have raised exception.')

    def test_annotate_private_type(self):
        try:
            self.client.annotate(self.handle, EXAMPLE_ANNOTATIONS, 'not_a_bool')
        except TypeError, e:
            self.failUnless(str(e) == 'private must be of type bool')
        else:
            self.fail('Should have raised exception.')


EXAMPLE_ANNOTATIONS_RESPONSE = {
    'private': {
        'venue': {
            'profitable': 'yes',
            'owner': 'John Doe'},
        'building': {
            'condition': 'poor'}
        },
    'public': {
        'venue': {
            'capacity': '28,037',
            'activity': 'sports'},
        'building': {
            'size': 'extra small',
            'material': 'wood',
            'ground': 'grass'}
        }
    }

EXAMPLE_ANNOTATIONS = {
    'venue': {
        'profitable': 'yes',
        'owner': 'John Doe'},
    'building': {
        'condition': 'poor'}
    }

EXAMPLE_ANNOTATE_RESPONSE = {'status': 'success'}


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_context
import unittest
import urllib
from decimal import Decimal as D

import mock

from simplegeo import Client
from simplegeo.models import Feature
from simplegeo.util import APIError, DecodeError

MY_OAUTH_KEY = 'MY_OAUTH_KEY'
MY_OAUTH_SECRET = 'MY_SECRET_KEY'
TESTING_LAYER = 'TESTING_LAYER'

API_VERSION = '1.0'
API_HOST = 'api.simplegeo.com'
API_PORT = 80

# example: http://api.simplegeo.com/0.1/context/37.797476,-122.424082.json

class ContextTest(unittest.TestCase):

    def setUp(self):
        self.client = Client(MY_OAUTH_KEY, MY_OAUTH_SECRET, host=API_HOST, port=API_PORT)
        self.query_lat = D('37.8016')
        self.query_lon = D('-122.4783')

    def _record(self):
        self.record_id += 1
        self.record_lat = (self.record_lat + 10) % 90
        self.record_lon = (self.record_lon + 10) % 180

        return Feature(
            layer=TESTING_LAYER,
            id=str(self.record_id),
            coordinates=(self.record_lat, self.record_lon)
        )

    def test_wrong_endpoint(self):
        self.assertRaises(Exception, self.client._endpoint, 'wrongwrong')

    def test_missing_argument(self):
        self.assertRaises(Exception, self.client._endpoint, 'context')

    def test_get_context(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.context.http = mockhttp

        res = self.client.context.get_context(self.query_lat, self.query_lon)
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/context/%s,%s.json' % (API_VERSION, self.query_lat, self.query_lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')
        # the code under test is required to have json-decoded this before handing it back
        self.failUnless(isinstance(res, dict), (type(res), repr(res)))

    @mock.patch('oauth2.Request.make_timestamp')
    @mock.patch('oauth2.Request.make_nonce')
    def test_oauth(self, mock_make_nonce, mock_make_timestamp):
        mock_make_nonce.return_value = 5
        mock_make_timestamp.return_value = 6

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.context.http = mockhttp

        self.client.context.get_context(self.query_lat, self.query_lon)

        self.assertEqual(mockhttp.method_calls[0][2]['body'], '')
        self.assertEqual(mockhttp.method_calls[0][2]['headers']['Authorization'], 'OAuth realm="http://api.simplegeo.com", oauth_body_hash="2jmj7l5rSw0yVb%2FvlWAYkK%2FYBwk%3D", oauth_nonce="5", oauth_timestamp="6", oauth_consumer_key="MY_OAUTH_KEY", oauth_signature_method="HMAC-SHA1", oauth_version="1.0", oauth_signature="aCYUTCHSeVlAQiu0CmG2tF71I74%3D"')

    def test_get_context_by_address(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.context.http = mockhttp

        addr = '41 Decatur St, San Francisco, CA'
        self.client.context.get_context_by_address(addr)
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/context/address.json?address=%s' % (API_VERSION, urllib.quote_plus(addr)))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_get_context_by_address(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.context.http = mockhttp

        self.client.context.get_context_from_bbox(
            D('37.69903420794415'), D('-122.4810791015625'),
            D('37.80001858607365'), D('-122.40554809570312'))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/context/37.69903420794415,-122.4810791015625,37.80001858607365,-122.40554809570312.json' % (API_VERSION))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_get_context_by_my_ip(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.context.http = mockhttp

        self.client.context.get_context_by_my_ip()
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/context/ip.json' % (API_VERSION,))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_get_context_by_ip(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.context.http = mockhttp

        ipaddr = '192.0.32.10'
        self.client.context.get_context_by_ip(ipaddr=ipaddr)
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/context/%s.json' % (API_VERSION, ipaddr))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_get_context_by_ip_invalid(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.context.http = mockhttp

        self.failUnlessRaises(ValueError, self.client.context.get_context_by_ip, '40.1,127.999')

    def test_get_context_invalid(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.context.http = mockhttp

        self.failUnlessRaises(ValueError, self.client.context.get_context, -91, 100)
        self.failUnlessRaises(ValueError, self.client.context.get_context, -11, 361)

    def test_get_context_no_body(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, None)
        self.client.context.http = mockhttp

        self.failUnlessRaises(DecodeError, self.client.context.get_context, self.query_lat, self.query_lon)
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/context/%s,%s.json' % (API_VERSION, self.query_lat, self.query_lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_get_context_bad_json(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY + 'some crap')
        self.client.context.http = mockhttp

        try:
            self.client.context.get_context(self.query_lat, self.query_lon)
        except DecodeError, e:
            self.failUnlessEqual(e.code,None,repr(e.code))
            self.failUnless("Could not decode" in e.msg, repr(e.msg))
            repr(e)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/context/%s,%s.json' % (API_VERSION, self.query_lat, self.query_lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_get_context_error(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '500', 'content-type': 'application/json', }, '{"message": "help my web server is confuzzled"}')
        self.client.context.http = mockhttp

        try:
            self.client.context.get_context(self.query_lat, self.query_lon)
        except APIError, e:
            self.failUnlessEqual(e.code, 500, repr(e.code))
            self.failUnlessEqual(e.msg, '{"message": "help my web server is confuzzled"}', (type(e.msg), repr(e.msg)))

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/context/%s,%s.json' % (API_VERSION, self.query_lat, self.query_lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_APIError(self):
        e = APIError(500, 'whee', {'status': "500"})
        self.failUnlessEqual(e.code, 500)
        self.failUnlessEqual(e.msg, 'whee')
        repr(e)
        str(e)

    def test_get_context_with_filter(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.context.http = mockhttp

        res = self.client.context.get_context(self.query_lat, self.query_lon, filter='weather,features')
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/context/%s,%s.json?filter=weather%%2Cfeatures' % (API_VERSION, self.query_lat, self.query_lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')
        # the code under test is required to have json-decoded this before handing it back
        self.failUnless(isinstance(res, dict), (type(res), repr(res)))

    def test_get_context_with_filter_and_context_args(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.context.http = mockhttp

        context_args = {
            'features__category': 'Neighborhood'
            }
        res = self.client.context.get_context(self.query_lat, self.query_lon, filter='weather,features', context_args=context_args)
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/context/%s,%s.json?filter=weather%%2Cfeatures&features__category=Neighborhood' % (API_VERSION, self.query_lat, self.query_lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')
        # the code under test is required to have json-decoded this before handing it back
        self.failUnless(isinstance(res, dict), (type(res), repr(res)))

EXAMPLE_BODY="""
{
   "weather": {
    "message" : "'NoneType' object has no attribute 'properties'",
    "code" : 400
    },
   "features": [
    {
     "name" : "06075013000",
     "type" : "Census Tract",
     "bounds": [
      -122.437326,
      37.795016,
      -122.42360099999999,
      37.799485
     ],
     "href" : "http://api.simplegeo.com/0.1/boundary/Census_Tract%3A06075013000%3A9q8zn0.json"
     },
     {
     "name" : "94123",
     "type" : "Postal",
     "bounds": [
      -122.452966,
      37.792787,
      -122.42360099999999,
      37.810798999999996
     ],
     "href" : "http://api.simplegeo.com/0.1/boundary/Postal%3A94123%3A9q8zjc.json"
     },
     {
     "name" : "San Francisco",
     "type" : "County",
     "bounds": [
      -123.173825,
      37.639829999999996,
      -122.28178,
      37.929823999999996
     ],
     "href" : "http://api.simplegeo.com/0.1/boundary/County%3ASan_Francisco%3A9q8yvv.json"
     },
     {
     "name" : "San Francisco",
     "type" : "City",
     "bounds": [
      -123.173825,
      37.639829999999996,
      -122.28178,
      37.929823999999996
     ],
     "href" : "http://api.simplegeo.com/0.1/boundary/City%3ASan_Francisco%3A9q8yvv.json"
     },
     {
     "name" : "Congressional District 8",
     "type" : "Congressional District",
     "bounds": [
      -122.612285,
      37.708131,
      -122.28178,
      37.929823999999996
     ],
     "href" : "http://api.simplegeo.com/0.1/boundary/Congressional_District%3ACongressional_Di%3A9q8yyn.json"
     },
     {
     "name" : "United States of America",
     "type" : "Country",
     "bounds": [
      -179.14247147726383,
      18.930137634111077,
      179.78114994357418,
      71.41217966730892
     ],
     "href" : "http://api.simplegeo.com/0.1/boundary/Country%3AUnited_States_of%3A9z12zg.json"
     },
     {
     "name" : "Pacific Heights",
     "type" : "Neighborhood",
     "bounds": [
      -122.446782,
      37.787529,
      -122.422182,
      37.797728
     ],
     "href" : "http://api.simplegeo.com/0.1/boundary/Neighborhood%3APacific_Heights%3A9q8yvz.json"
     },
     {
     "name" : "San Francisco1",
     "type" : "Urban Area",
     "bounds": [
      -122.51666666668193,
      37.19166666662851,
      -121.73333333334497,
      38.04166666664091
     ],
     "href" : "http://api.simplegeo.com/0.1/boundary/Urban_Area%3ASan_Francisco1%3A9q9jsg.json"
     },
     {
     "name" : "California",
     "type" : "Province",
     "bounds": [
      -124.48200299999999,
      32.528832,
      -114.131211,
      42.009516999999995
     ],
     "href" : "http://api.simplegeo.com/0.1/boundary/Province%3ACA%3A9qdguu.json"
     }
   ],
   "demographics": {
    "metro_score" : "10"
    }
   }
"""


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_places
# -*- coding: utf-8 -*-

import unittest
import urllib
from decimal import Decimal as D

import simplegeo.json as json
import mock

from simplegeo import Client
from simplegeo.models import Feature
from simplegeo.util import APIError, DecodeError

MY_OAUTH_KEY = 'MY_OAUTH_KEY'
MY_OAUTH_SECRET = 'MY_SECRET_KEY'
TESTING_LAYER = 'TESTING_LAYER'

API_VERSION = '1.0'
API_HOST = 'api.simplegeo.com'
API_PORT = 80

class PlacesTest(unittest.TestCase):

    def setUp(self):
        self.client = Client(MY_OAUTH_KEY, MY_OAUTH_SECRET, host=API_HOST, port=API_PORT)

    def test_wrong_endpoint(self):
        self.assertRaises(Exception, self.client._endpoint, 'featuret')

    def test_missing_argument(self):
        self.assertRaises(Exception, self.client._endpoint, 'features')

    def test_add_feature_norecord_id_nonascii_nonutf8_bytes(self):
        mockhttp = mock.Mock()
        handle = 'SG_abcdefghijklmnopqrstuv'
        newloc = 'http://api.simplegeo.com:80/%s/places/%s.json' % (API_VERSION, handle)
        properties = {
            'name': "B\x92b's H\x92use of M\x92nkeys"
            }
        resultfeature = Feature((D('11.03'), D('10.03')), simplegeohandle=handle, properties=properties)
        methods_called = []
        def mockrequest2(*args, **kwargs):
            methods_called.append(('request', args, kwargs))
            return ({'status': '200', 'content-type': 'application/json', }, resultfeature.to_json())

        def mockrequest(*args, **kwargs):
            self.assertEqual(args[0], 'http://api.simplegeo.com:80/%s/places' % (API_VERSION,))
            self.assertEqual(args[1], 'POST')

            bodyobj = json.loads(kwargs['body'])
            self.failUnless(not hasattr(bodyobj, 'id'))
            methods_called.append(('request', args, kwargs))
            mockhttp.request = mockrequest2
            return ({'status': '202', 'content-type': 'application/json', 'location': newloc}, json.dumps({'id': handle}))

        mockhttp.request = mockrequest
        self.client.places.http = mockhttp

        feature = Feature(
            coordinates=(D('37.8016'), D('-122.4783'))
        )

        res = self.client.places.add_feature(feature)
        self.failUnlessEqual(res, handle)

    def test_add_feature_norecord_id_nonascii(self):
        mockhttp = mock.Mock()
        handle = 'SG_abcdefghijklmnopqrstuv'
        newloc = 'http://api.simplegeo.com:80/%s/places/%s.json' % (API_VERSION, handle)
        properties = {
            'name': u"B❦b's H❤use of M❥nkeys"
            }
        resultfeature = Feature((D('11.03'), D('10.03')), simplegeohandle=handle, properties=properties)
        methods_called = []
        def mockrequest2(*args, **kwargs):
            methods_called.append(('request', args, kwargs))
            return ({'status': '200', 'content-type': 'application/json', }, resultfeature.to_json())

        def mockrequest(*args, **kwargs):
            self.assertEqual(args[0], 'http://api.simplegeo.com:80/%s/places' % (API_VERSION,))
            self.assertEqual(args[1], 'POST')

            bodyobj = json.loads(kwargs['body'])
            self.failUnless(not hasattr(bodyobj, 'id'))
            methods_called.append(('request', args, kwargs))
            mockhttp.request = mockrequest2
            return ({'status': '202', 'content-type': 'application/json', 'location': newloc}, json.dumps({'id': handle}))

        mockhttp.request = mockrequest
        self.client.places.http = mockhttp

        feature = Feature(
            coordinates=(D('37.8016'), D('-122.4783'))
        )

        res = self.client.places.add_feature(feature)
        self.failUnlessEqual(res, handle)

    def test_add_feature_norecord_id(self):
        mockhttp = mock.Mock()
        handle = 'SG_abcdefghijklmnopqrstuv'
        newloc = 'http://api.simplegeo.com:80/%s/places/%s.json' % (API_VERSION, handle)
        resultfeature = Feature((D('11.03'), D('10.03')), simplegeohandle=handle)
        methods_called = []
        def mockrequest2(*args, **kwargs):
            methods_called.append(('request', args, kwargs))
            return ({'status': '200', 'content-type': 'application/json', }, resultfeature.to_json())

        def mockrequest(*args, **kwargs):
            self.assertEqual(args[0], 'http://api.simplegeo.com:80/%s/places' % (API_VERSION,))
            self.assertEqual(args[1], 'POST')

            bodyobj = json.loads(kwargs['body'])
            self.failUnless(not hasattr(bodyobj, 'id'))
            methods_called.append(('request', args, kwargs))
            mockhttp.request = mockrequest2
            return ({'status': '202', 'content-type': 'application/json', 'location': newloc}, json.dumps({'id': handle}))

        mockhttp.request = mockrequest
        self.client.places.http = mockhttp

        feature = Feature(
            coordinates=(D('37.8016'), D('-122.4783'))
        )

        res = self.client.places.add_feature(feature)
        self.failUnlessEqual(res, handle)

    def test_add_feature_simplegeohandle(self):
        handle = 'SG_abcdefghijklmnopqrstuv'
        feature = Feature(
            simplegeohandle=handle,
            coordinates=(D('37.8016'), D('-122.4783'))
        )

        # You can't add-feature on a feature that already has a simplegeo handle. Don't do that.
        self.failUnlessRaises(ValueError, self.client.places.add_feature, feature)

    def test_add_feature_simplegeohandle_and_record_id(self):
        handle = 'SG_abcdefghijklmnopqrstuv'
        record_id = 'this is my record #1. my first record. and it is mine'
        feature = Feature(
            simplegeohandle=handle,
            properties={'record_id': record_id},
            coordinates = (D('37.8016'), D('-122.4783'))
        )

        # You can't add-feature on a feature that already has a simplegeo handle. Don't do that.
        self.failUnlessRaises(ValueError, self.client.places.add_feature, feature)

    def test_add_feature_record_id(self):
        mockhttp = mock.Mock()
        handle = 'SG_abcdefghijklmnopqrstuv'
        record_id = 'this is my record #1. my first record. and it is mine'
        newloc = 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle)
        resultfeature = Feature((D('11.03'), D('10.03')), simplegeohandle=handle)
        methods_called = []
        def mockrequest2(*args, **kwargs):
            methods_called.append(('request', args, kwargs))
            return ({'status': '200', 'content-type': 'application/json', }, resultfeature.to_json())

        def mockrequest(*args, **kwargs):
            self.failUnlessEqual(args[0], 'http://api.simplegeo.com:80/%s/places' % (API_VERSION,))
            self.failUnlessEqual(args[1], 'POST')
            bodyobj = json.loads(kwargs['body'])
            self.failUnlessEqual(bodyobj['properties'].get('record_id'), record_id)
            methods_called.append(('request', args, kwargs))
            mockhttp.request = mockrequest2
            return ({'status': '202', 'content-type': 'application/json', 'location': newloc}, json.dumps({'id': handle}))

        mockhttp.request = mockrequest
        self.client.places.http = mockhttp

        feature = Feature(
            properties={'record_id': record_id},
            coordinates = (D('37.8016'), D('-122.4783'))
        )

        res = self.client.places.add_feature(feature)
        self.failUnlessEqual(res, handle)

    def test_get_feature(self):
        handle = 'SG_abcdefghijklmnopqrstuv'
        resultfeature = Feature((D('11.03'), D('10.03')), simplegeohandle=handle)

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, resultfeature.to_json())
        self.client.places.http = mockhttp

        res = self.client.places.get_feature(handle)
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')
        self.failUnless(isinstance(res, Feature), res)
        self.assertEqual(res.to_json(), resultfeature.to_json())

    def test_empty_body(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, None)
        self.client.places.http = mockhttp

        self.client.places._request("http://anyrandomendpoint", 'POST')

        self.failUnless(mockhttp.method_calls[0][2]['body'] is None, (repr(mockhttp.method_calls[0][2]['body']), type(mockhttp.method_calls[0][2]['body'])))

    def test_dont_json_decode_results(self):
        """ _request() is required to return the exact string that the HTTP
        server sent to it -- no transforming it, such as by json-decoding. """

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, '{ "Hello": "I am a string. \xe2\x9d\xa4" }'.decode('utf-8'))
        self.client.places.http = mockhttp
        res = self.client.places._request("http://thing", 'POST')[1]
        self.failUnlessEqual(res, '{ "Hello": "I am a string. \xe2\x9d\xa4" }'.decode('utf-8'))

    def test_dont_Featureify_results(self):
        """ _request() is required to return the exact string that the HTTP
        server sent to it -- no transforming it, such as by json-decoding and
        then constructing a Feature. """

        EXAMPLE_RECORD_JSONSTR=json.dumps({ 'geometry' : { 'type' : 'Point', 'coordinates' : [D('10.0'), D('11.0')] }, 'id' : 'my_id', 'type' : 'Feature', 'properties' : { 'key' : 'value'  , 'type' : 'object' } })

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_RECORD_JSONSTR)
        self.client.places.http = mockhttp
        res = self.client.places._request("http://thing", 'POST')[1]
        self.failUnlessEqual(res, EXAMPLE_RECORD_JSONSTR)

    def test_update_feature(self):
        handle = 'SG_abcdefghijklmnopqrstuv'
        rec = Feature((D('11.03'), D('10.04')), simplegeohandle=handle)

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, {'token': "this is your polling token"})
        self.client.places.http = mockhttp

        res = self.client.places.update_feature(rec)
        self.failUnless(isinstance(res, dict), res)
        self.failUnless(res.has_key('token'), res)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'POST')
        bodyjson = mockhttp.method_calls[0][2]['body']
        self.failUnless(isinstance(bodyjson, basestring), (repr(bodyjson), type(bodyjson)))
        # If it decoded as valid json then check for some expected fields
        bodyobj = json.loads(bodyjson)
        self.failUnless(bodyobj.get('geometry').has_key('coordinates'), bodyobj)
        self.failUnless(bodyobj.get('geometry').has_key('type'), bodyobj)
        self.failUnlessEqual(bodyobj.get('geometry')['type'], 'Point')

    def test_delete_feature(self):
        handle = 'SG_abcdefghijklmnopqrstuv'

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, "whatever the response body is")
        self.client.places.http = mockhttp

        res = self.client.places.delete_feature(handle)
        self.failUnlessEqual(res, "whatever the response body is")

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'DELETE')

    def test_search_nonascii(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': u"B❤b's House Of Monkeys", 'category': u"m❤nkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': u"M❤nkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        self.failUnlessRaises(ValueError, self.client.places.search, -91, 100)
        self.failUnlessRaises(ValueError, self.client.places.search, -81, 361)

        lat = D('11.03')
        lon = D('10.04')
        res = self.client.places.search(lat, lon, query=u'm❤nkey', category='animal')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        urlused = mockhttp.method_calls[0][1][0]
        urlused = urllib.unquote(urlused).decode('utf-8')
        self.assertEqual(urlused, u'http://api.simplegeo.com:80/%s/places/%s,%s.json?q=m❤nkey&category=animal' % (API_VERSION, lat, lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_search(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        self.failUnlessRaises(ValueError, self.client.places.search, -91, 100)
        self.failUnlessRaises(ValueError, self.client.places.search, -81, 361)

        lat = D('11.03')
        lon = D('10.04')
        res = self.client.places.search(lat, lon, query='monkeys', category='animal')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/%s,%s.json?q=monkeys&category=animal' % (API_VERSION, lat, lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_search_by_ip_nonascii(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': u"Bob's House Of M❤nkeys", 'category': u"m❤nkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': u"M❤nkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        self.failUnlessRaises(ValueError, self.client.places.search_by_ip, 'this is not an IP address at all, silly')
        self.failUnlessRaises(ValueError, self.client.places.search_by_ip, -81, 181) # Someone accidentally passed lat, lon to search_by_ip().

        ipaddr = '192.0.32.10'

        res = self.client.places.search_by_ip(ipaddr, query=u'm❤nkey', category='animal')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        urlused = mockhttp.method_calls[0][1][0]
        urlused = urllib.unquote(urlused).decode('utf-8')
        self.assertEqual(urlused, u'http://api.simplegeo.com:80/%s/places/%s.json?q=m❤nkey&category=animal' % (API_VERSION, ipaddr))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

        res = self.client.places.search_by_ip(ipaddr, query=u'm❤nkey', category=u'❤nimal')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[-1][0], 'request')
        urlused = mockhttp.method_calls[-1][1][0]
        urlused = urllib.unquote(urlused).decode('utf-8')
        self.assertEqual(urlused, u'http://api.simplegeo.com:80/%s/places/%s.json?q=m❤nkey&category=❤nimal' % (API_VERSION, ipaddr))
        self.assertEqual(mockhttp.method_calls[-1][1][1], 'GET')

    def test_search_by_ip(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        self.failUnlessRaises(ValueError, self.client.places.search_by_ip, 'this is not an IP address at all, silly')
        self.failUnlessRaises(ValueError, self.client.places.search_by_ip, -81, 181) # Someone accidentally passed lat, lon to search_by_ip().

        ipaddr = '192.0.32.10'

        res = self.client.places.search_by_ip(ipaddr, query='monkeys', category='animal')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/%s.json?q=monkeys&category=animal' % (API_VERSION, ipaddr))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_search_by_my_ip_nonascii(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        ipaddr = '192.0.32.10'
        self.failUnlessRaises(ValueError, self.client.places.search_by_my_ip, ipaddr) # Someone accidentally passed an ip addr to search_by_my_ip().

        res = self.client.places.search_by_my_ip(query='monk❥y', category='animal')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[-1][0], 'request')
        urlused = mockhttp.method_calls[-1][1][0]
        urlused = urllib.unquote(urlused).decode('utf-8')
        self.assertEqual(urlused, u'http://api.simplegeo.com:80/%s/places/ip.json?q=monk❥y&category=animal' % (API_VERSION,))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

        res = self.client.places.search_by_my_ip(query='monk❥y', category='anim❥l')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[-1][0], 'request')
        urlused = mockhttp.method_calls[-1][1][0]
        urlused = urllib.unquote(urlused).decode('utf-8')
        self.assertEqual(urlused, u'http://api.simplegeo.com:80/%s/places/ip.json?q=monk❥y&category=anim❥l' % (API_VERSION,))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_search_by_my_ip(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        ipaddr = '192.0.32.10'
        self.failUnlessRaises(ValueError, self.client.places.search_by_my_ip, ipaddr) # Someone accidentally passed an ip addr to search_by_my_ip().

        res = self.client.places.search_by_my_ip(query='monkeys', category='animal')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/ip.json?q=monkeys&category=animal' % (API_VERSION,))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_search_by_address_nonascii(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        lat = D('11.03')
        lon = D('10.04')
        self.failUnlessRaises(ValueError, self.client.places.search_by_address, lat, lon) # Someone accidentally passed a lat,lon to search_by_address().

        addr = u'41 Decatur St, San Francisc❦, CA'
        res = self.client.places.search_by_address(addr, query='monkeys', category='animal')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[-1][0], 'request')
        urlused = mockhttp.method_calls[-1][1][0]
        cod = urllib.quote_plus(addr.encode('utf-8'))
        self.assertEqual(urlused, 'http://api.simplegeo.com:80/%s/places/address.json?q=monkeys&category=animal&address=%s' % (API_VERSION, cod,))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

        res = self.client.places.search_by_address(addr, query=u'monke❦s', category=u'ani❦al')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[-1][0], 'request')
        urlused = mockhttp.method_calls[-1][1][0]

        quargs = {'q': u'monke❦s', 'category': u'ani❦al', 'address': addr}
        equargs = dict( (k, v.encode('utf-8')) for k, v in quargs.iteritems() )
        s2quargs = urllib.urlencode(equargs)
        self.assertEqual(urlused, 'http://api.simplegeo.com:80/%s/places/address.json?%s' % (API_VERSION, s2quargs))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_search_by_address(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        lat = D('11.03')
        lon = D('10.04')
        self.failUnlessRaises(ValueError, self.client.places.search_by_address, lat, lon) # Someone accidentally passed a lat,lon to search_by_address().

        addr = '41 Decatur St, San Francisco, CA'
        res = self.client.places.search_by_address(addr, query='monkeys', category='animal')
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/address.json?q=monkeys&category=animal&address=%s' % (API_VERSION, urllib.quote_plus(addr)))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_radius_search(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': []}))
        self.client.places.http = mockhttp

        lat = D('11.03')
        lon = D('10.04')
        radius = D('0.01')
        res = self.client.places.search(lat, lon, radius=radius)
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 0)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/%s,%s.json?radius=%s' % (API_VERSION, lat, lon, radius))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_radius_search_by_ip(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': []}))
        self.client.places.http = mockhttp

        ipaddr = '192.0.32.10'
        radius = D('0.01')
        res = self.client.places.search_by_ip(ipaddr, radius=radius)
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 0)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/%s.json?radius=%s' % (API_VERSION, ipaddr, radius))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_radius_search_by_my_ip(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': []}))
        self.client.places.http = mockhttp

        ipaddr = '192.0.32.10'
        radius = D('0.01')
        self.failUnlessRaises((AssertionError, TypeError), self.client.places.search_by_my_ip, ipaddr, radius=radius) # Someone accidentally passed an ip addr to search_by_my_ip().

        res = self.client.places.search_by_my_ip(radius=radius)
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 0)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/ip.json?radius=%s' % (API_VERSION, radius))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_radius_search_by_address(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': []}))
        self.client.places.http = mockhttp

        lat = D('11.03')
        lon = D('10.04')
        radius = D('0.01')
        self.failUnlessRaises((AssertionError, TypeError), self.client.places.search_by_address, lat, lon, radius=radius) # Someone accidentally passed a lat,lon to search_by_address().

        addr = '41 Decatur St, San Francisco, CA'
        res = self.client.places.search_by_address(addr, radius=radius)
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 0)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/address.json?radius=%s&address=%s' % (API_VERSION, radius, urllib.quote_plus(addr)))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_no_terms_search(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        lat = D('11.03')
        lon = D('10.04')
        res = self.client.places.search(lat, lon)
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/%s,%s.json' % (API_VERSION, lat, lon))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_no_terms_search_by_ip(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        ipaddr = '192.0.32.10'
        res = self.client.places.search_by_ip(ipaddr)
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/%s.json' % (API_VERSION, ipaddr))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_no_terms_search_by_my_ip(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        ipaddr = '192.0.32.10'
        self.failUnlessRaises(ValueError, self.client.places.search_by_my_ip, ipaddr) # Someone accidentally passed an ip addr to search_by_my_ip().
        res = self.client.places.search_by_my_ip()
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/ip.json' % (API_VERSION,))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_no_terms_search_by_address(self):
        rec1 = Feature((D('11.03'), D('10.04')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Bob's House Of Monkeys", 'category': "monkey dealership"})
        rec2 = Feature((D('11.03'), D('10.05')), simplegeohandle='SG_abcdefghijkmlnopqrstuv', properties={'name': "Monkey Food 'R' Us", 'category': "pet food store"})

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, json.dumps({'type': "FeatureColllection", 'features': [rec1.to_dict(), rec2.to_dict()]}))
        self.client.places.http = mockhttp

        lat = D('11.03')
        lon = D('10.04')
        self.failUnlessRaises(ValueError, self.client.places.search_by_address, lat, lon) # Someone accidentally passed a lat,lon search_by_address().

        addr = '41 Decatur St, San Francisco, CA'
        res = self.client.places.search_by_address(addr)
        self.failUnless(isinstance(res, (list, tuple)), (repr(res), type(res)))
        self.failUnlessEqual(len(res), 2)
        self.failUnless(all(isinstance(f, Feature) for f in res))
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/places/address.json?address=%s' % (API_VERSION, urllib.quote_plus(addr)))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_get_feature_bad_json(self):
        handle = 'SG_abcdefghijklmnopqrstuv'

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, 'some crap')
        self.client.places.http = mockhttp

        try:
            self.client.places.get_feature(handle)
        except DecodeError, e:
            self.failUnlessEqual(e.code,None,repr(e.code))
            self.failUnless("Could not decode JSON" in e.msg, repr(e.msg))
            repr(e)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_APIError(self):
        e = APIError(500, 'whee', {'status': "500"})
        self.failUnlessEqual(e.code, 500)
        self.failUnlessEqual(e.msg, 'whee')
        repr(e)
        str(e)

    def test_get_places_error(self):
        handle = 'SG_abcdefghijklmnopqrstuv'

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '500', 'content-type': 'application/json', }, '{"message": "help my web server is confuzzled"}')
        self.client.places.http = mockhttp

        try:
            self.client.places.get_feature(handle)
        except APIError, e:
            self.failUnlessEqual(e.code, 500, repr(e.code))
            self.failUnlessEqual(e.msg, '{"message": "help my web server is confuzzled"}', (type(e.msg), repr(e.msg)))

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, handle))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_feature
import unittest
import re
from simplegeo.models import Feature
from simplegeo.util import deep_swap
from decimal import Decimal as D

class FeatureTest(unittest.TestCase):

    def test_geojson_is_correct(self):
        f = Feature(coordinates=[-90, D('171.0')], properties={'record_id': 'my_id'}, strict_lon_validation=True)
        stringy = f.to_json()
        self.failUnlessEqual(stringy, '{"geometry": {"type": "Point", "coordinates": [171.0, -90]}, "type": "Feature", "properties": {"record_id": "my_id", "private": false}}')

    def test_swapper(self):
        t1 = (2, 1)
        self.failUnlessEqual(deep_swap(t1), (1, 2))

        linestring1 = [(2, 1), (4, 3), (6, 5), (8, 7)]
        self.failUnlessEqual(
            deep_swap(linestring1),
            [(1, 2), (3, 4), (5, 6), (7, 8)]
            )

        multipolygon1 = [
            [[[102.0, 2.0], [103.0, 2.0], [103.0, 3.0], [102.0, 3.0], [102.0, 2.0]]],
            [[[100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0]],
             [[100.2, 0.2], [100.8, 0.2], [100.8, 0.8], [100.2, 0.8], [100.2, 0.2]]]
            ]

        self.failUnlessEqual(deep_swap(multipolygon1),
                             [[[(2.0, 102.0), (2.0, 103.0), (3.0, 103.0), (3.0, 102.0), (2.0, 102.0)]], [[(0.0, 100.0), (0.0, 101.0), (1.0, 101.0), (1.0, 100.0), (0.0, 100.0)], [(0.2, 100.2), (0.2, 100.8), (0.8, 100.8), (0.8, 100.2), (0.2, 100.2)]]]
                             )

    def test_record_constructor_useful_validation_error_message(self):
        try:
            Feature(coordinates=[181, D('10.0')], properties={'record_id': 'my_id'})
        except TypeError, e:
            #self.failUnless(str(e).startswith('The first argument'), str(e))
            self.failUnless('is required to be a 2-element sequence' in str(e), str(e))
        else:
            self.fail('Should have raised exception.')

        try:
            Feature(coordinates=[-90, D('181.0')], properties={'record_id': 'my_id'}, strict_lon_validation=True)
        except TypeError, e:
            self.failUnless('181' in str(e), str(e))
        else:
            self.fail('Should have raised exception.')

        try:
            Feature(coordinates=[-90, D('361.0')], properties={'record_id': 'my_id'})
        except TypeError, e:
            self.failUnless('361' in str(e), str(e))
        else:
            self.fail('Should have raised exception.')

        try:
            Feature(coordinates=['-90', D('361.0')], properties={'record_id': 'my_id'})
        except TypeError, e:
            err_msg_re = re.compile("argument is required to be.*number.*not: .*<type 'str'")
            self.failUnless(err_msg_re.search(str(e)), str(e))
        else:
            self.fail('Should have raised exception.')

    def test_record_constructor(self):
        self.failUnlessRaises(TypeError, Feature, D('11.0'), D('10.0'), properties={'record_id': 'my_id'})

        # lat exceeds bound
        self.failUnlessRaises(TypeError, Feature, (D('91.0'), D('10.1')), properties={'record_id': 'my_id'})

        # lon exceeds bound
        self.failUnlessRaises(TypeError, Feature, (D('10.1'), D('180.1')), properties={'record_id': 'my_id'}, strict_lon_validation=True)

        record = Feature(coordinates=(D('11.0'), D('10.0')), properties={'record_id': 'my_id'})
        self.failUnlessEqual(record.properties.get('record_id'), 'my_id')
        self.failUnless(not hasattr(record, 'id'))
        self.failUnlessEqual(record.geomtype, 'Point')
        self.failUnlessEqual(record.coordinates[0], D('11.0'))
        self.failUnlessEqual(record.coordinates[1], D('10.0'))

        record = Feature(coordinates=(D('11.0'), D('10.0')), simplegeohandle='SG_abcdefghijklmnopqrstuv')
        self.failUnlessEqual(record.properties.get('record_id'), None)
        self.failUnlessEqual(record.id, 'SG_abcdefghijklmnopqrstuv')

        record = Feature(coordinates=(D('11.0'), D('10.0')), properties={'record_id': 'my_id'}, simplegeohandle='SG_abcdefghijklmnopqrstuv')
        self.failUnlessEqual(record.properties.get('record_id'), 'my_id')
        self.failUnlessEqual(record.id, 'SG_abcdefghijklmnopqrstuv')

        record = Feature(coordinates=(D('11.0'), D('10.0')))
        self.failUnlessEqual(record.properties.get('record_id'), None)
        self.failUnless(not hasattr(record, 'id'))

        record = Feature((D('11.0'), D('10.0')), properties={'record_id': 'my_id'})
        self.failUnlessEqual(record.properties.get('record_id'), 'my_id')

        record = Feature((11.0, 10.0), properties={'record_id': 'my_id'})
        self.failUnlessEqual(record.geomtype, 'Point')
        self.failUnlessEqual(record.coordinates[0], 11.0)
        self.failUnlessEqual(record.coordinates[1], 10.0)
        self.failUnlessEqual(record.properties.get('record_id'), 'my_id')

        record = Feature([[(11.0, 179.9), (12, -179.9)]], geomtype='Polygon')
        self.failUnlessEqual(record.geomtype, 'Polygon')
        self.failUnlessEqual(len(record.coordinates[0]), 2)
        self.failUnlessEqual(record.coordinates[0][0], (11.0, 179.9))

        jsondict = record.to_dict()
        self.failUnlessEqual(jsondict['geometry']['coordinates'][0][0], (179.9, 11.))

    def test_record_from_dict_lon_validation(self):
        record_dict = {
                     'geometry' : {
                                   'type' : 'Point',
                                   'coordinates' : [D('181.0'), D('11.0')]
                                   },
                     'type' : 'Feature',
                     'properties' : {
                                     'record_id' : 'my_id',
                                     'key' : 'value'  ,
                                     'type' : 'object'
                                     }
                     }

        self.failUnlessRaises(ValueError, Feature.from_dict, record_dict, True)
        record = Feature.from_dict(record_dict, strict_lon_validation=False)
        self.assertEquals(record.coordinates[0], D('11.0'))
        self.assertEquals(record.coordinates[1], D('181.0'))
        self.assertEquals(record.properties.get('record_id'), 'my_id')
        self.assertEquals(record.properties['key'], 'value')
        self.assertEquals(record.properties['type'], 'object')

    def test_record_from_dict(self):
        record_dict = {
                     'geometry' : {
                                   'type' : 'Point',
                                   'coordinates' : [D('10.0'), D('11.0')]
                                   },
                     'type' : 'Feature',
                     'properties' : {
                                     'record_id' : 'my_id',
                                     'key' : 'value'  ,
                                     'type' : 'object'
                                     }
                     }

        record = Feature.from_dict(record_dict)
        self.assertEquals(record.coordinates[0], D('11.0'))
        self.assertEquals(record.coordinates[1], D('10.0'))
        self.assertEquals(record.properties.get('record_id'), 'my_id')
        self.assertEquals(record.properties['key'], 'value')
        self.assertEquals(record.properties['type'], 'object')

        self.assertEquals(record.to_json(), '{"geometry": {"type": "Point", "coordinates": [10.0, 11.0]}, "type": "Feature", "properties": {"record_id": "my_id", "type": "object", "private": false, "key": "value"}}')

        record_dict = {
                     'geometry' : {
                                   'type' : 'Point',
                                   'coordinates' : [D('10.0'), D('11.0')]
                                   },
                     'id' : 'SG_abcdefghijklmnopqrstuv',
                     'type' : 'Feature',
                     'properties' : {
                                     'key' : 'value'  ,
                                     'type' : 'object'
                                     }
                     }

        record = Feature.from_dict(record_dict)
        self.assertEquals(record.properties.get('record_id'), None)
        self.assertEquals(record.id, 'SG_abcdefghijklmnopqrstuv')

        record_dict = {
                     'geometry' : {
                                   'type' : 'Point',
                                   'coordinates' : [D('10.0'), D('11.0')]
                                   },
                     'id' : 'SG_abcdefghijklmnopqrstuv',
                     'type' : 'Feature',
                     'properties' : {
                                     'record_id' : 'my_id',
                                     'key' : 'value'  ,
                                     'type' : 'object'
                                     }
                     }

        record = Feature.from_dict(record_dict)
        self.assertEquals(record.properties.get('record_id'), 'my_id')
        self.assertEquals(record.id, 'SG_abcdefghijklmnopqrstuv')

        record_dict = {
                     'geometry' : {
                                   'type' : 'Point',
                                   'coordinates' : [10.0, 11.0]
                                   },
                     'type' : 'Feature',
                     'properties' : {
                                     'record_id' : 'my_id',
                                     'key' : 'value'  ,
                                     'type' : 'object'
                                     }
                     }

        record = Feature.from_dict(record_dict)
        self.assertEquals(record.coordinates[0], 11.0)
        self.assertEquals(record.coordinates[1], 10.0)

    def test_record_to_dict_sets_id_correctly(self):
        handle = 'SG_abcdefghijklmnopqrstuv'
        record_id = 'this is my record #1. my first record. and it is mine'
        rec = Feature(coordinates=(D('11.03'), D('10.03')), simplegeohandle=handle, properties={'record_id': record_id})
        dic = rec.to_dict()
        self.failUnlessEqual(dic.get('id'), handle)
        self.failUnlessEqual(dic.get('properties', {}).get('record_id'), record_id)

        rec = Feature(coordinates=(D('11.03'), D('10.03')), simplegeohandle=handle, properties={'record_id': None})
        dic = rec.to_dict()
        self.failUnlessEqual(dic.get('id'), handle)
        self.failUnlessEqual(dic.get('properties', {}).get('record_id'), None)

        rec = Feature(coordinates=(D('11.03'), D('10.03')), simplegeohandle=handle, properties={'record_id': None})
        dic = rec.to_dict()
        self.failUnlessEqual(dic.get('id'), handle)
        self.failUnlessEqual(dic.get('properties', {}).get('record_id'), None)

        rec = Feature(coordinates=(D('11.03'), D('10.03')), simplegeohandle=None, properties={'record_id': None})
        dic = rec.to_dict()
        self.failUnlessEqual(dic.get('id'), None)
        self.failUnlessEqual(dic.get('properties', {}).get('record_id'), None)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_record
import unittest
from simplegeo import Record

class RecordTest(unittest.TestCase):

    def test_record_from_dict(self):
        record_dict = {'created': 10,
                     'geometry' : {
                                   'type' : 'Point',
                                   'coordinates' : [10.0, 11.0]
                                   },
                     'id' : 'my_id',
                     'type' : 'Feature',
                     'properties' : {
                                     'layer' : 'my_layer',
                                     'key' : 'value'  ,
                                     'type' : 'object'
                                     }
                     }

        record = Record.from_dict(record_dict)
        self.assertEquals(record.created, record_dict['created'])
        self.assertEquals(record.lat, 11.0)
        self.assertEquals(record.lon, 10.0)
        self.assertEquals(record.id, 'my_id')
        self.assertEquals(record.layer, 'my_layer')
        self.assertEquals(record.key, 'value')
        self.assertEquals(record.type, 'object')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = util
import re
import ipaddr
import simplegeo.json as json
from decimal import Decimal as D

def json_decode(jsonstr):
    try:
        return json.loads(jsonstr)
    except (ValueError, TypeError), le:
        raise DecodeError(jsonstr, le)

def is_numeric(x):
    return isinstance(x, (int, long, float, D))

def swap(tupleab):
    return (tupleab[1], tupleab[0])

def deep_swap(struc):
    if is_numeric(struc[0]):
        if len(struc) != 2:
            raise ValueError("Strucs must be (val, val)")
        if not is_numeric(struc[1]):
            raise ValueError("Strucs must contain numerics.")
        return swap(struc)
    return [deep_swap(sub) for sub in struc]

def _assert_valid_lat(x):
    if not is_valid_lat(x):
        raise ValueError("not a valid lat: %s" % (x,))

def _assert_valid_lon(x, strict=False):
    if not is_valid_lon(x, strict=strict):
        raise ValueError("not a valid lon (strict=%s): %s" % (strict, x,))

def is_valid_lat(x):
    return is_numeric(x) and (x <= 90) and (x >= -90)

def is_valid_lon(x, strict=False):
    """
    Longitude is technically defined as extending from -180 to
    180. However in practice people sometimes prefer to use longitudes
    which have "wrapped around" past 180. For example, if you are
    drawing a polygon around modern-day Russia almost all of it is in
    the Eastern Hemisphere, which means its longitudes are almost all
    positive numbers, but the easternmost part of it (Big Diomede
    Island) lies a few degrees east of the International Date Line,
    and it is sometimes more convenient to describe it as having
    longitude 190.9 instead of having longitude -169.1.

    If strict=True then is_valid_lon() requires a number to be in
    [-180..180] to be considered a valid longitude. If strict=False
    (the default) then it requires the number to be in [-360..360].
    """
    if strict:
        return is_numeric(x) and (x <= 180) and (x >= -180)
    else:
        return is_numeric(x) and (x <= 360) and (x >= -360)

def deep_validate_lat_lon(struc, strict_lon_validation=False):
    """
    For the meaning of strict_lon_validation, please see the function
    is_valid_lon().
    """
    if not isinstance(struc, (list, tuple, set)):
        raise TypeError('argument is required to be a sequence (of sequences of...) numbers, not: %s :: %s' % (struc, type(struc)))
    if is_numeric(struc[0]):
        if not len(struc) == 2:
            raise TypeError("The leaf element of this structure is required to be a tuple of length 2 (to hold a lat and lon).")

        _assert_valid_lat(struc[0])
        _assert_valid_lon(struc[1], strict=strict_lon_validation)
    else:
        for sub in struc:
            deep_validate_lat_lon(sub, strict_lon_validation=strict_lon_validation)
    return True

def is_valid_ip(ip):
    try:
        ipaddr.IPAddress(ip)
    except ValueError:
        return False
    else:
        return True

SIMPLEGEOHANDLE_RSTR=r"""SG_[A-Za-z0-9]{22}(?:_-?[0-9]{1,3}(?:\.[0-9]+)?_-?[0-9]{1,3}(?:\.[0-9]+)?)?(?:@-?[0-9]+)?$"""
SIMPLEGEOHANDLE_R= re.compile(SIMPLEGEOHANDLE_RSTR)
def is_simplegeohandle(s):
    return isinstance(s, basestring) and SIMPLEGEOHANDLE_R.match(s)

def to_unicode(s):
    """ Convert to unicode, raise exception with instructive error
    message if s is not unicode, ascii, or utf-8. """
    if not isinstance(s, unicode):
        if not isinstance(s, str):
            raise TypeError('You are required to pass either unicode or string here, not: %r (%s)' % (type(s), s))
        try:
            s = s.decode('utf-8')
        except UnicodeDecodeError, le:
            raise TypeError('You are required to pass either a unicode object or a utf-8 string here. You passed a Python string object which contained non-utf-8: %r. The UnicodeDecodeError that resulted from attempting to interpret it as utf-8 was: %s' % (s, le,))
    return s


"""Exceptions."""

class APIError(Exception):
    """Base exception for all API errors."""

    def __init__(self, code, msg, headers, description=''):
        self.code = code
        self.msg = msg
        self.headers = headers
        self.description = description

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "%s (#%s) %s" % (self.msg, self.code, self.description)


class DecodeError(APIError):
    """There was a problem decoding the API's response, which was
    supposed to be encoded in JSON, but which apparently wasn't."""

    def __init__(self, body, le):
        super(DecodeError, self).__init__(None, "Could not decode JSON from server.", None, repr(le))
        self.body = body

    def __repr__(self):
        return "%s content: %s" % (self.description, self.body)



########NEW FILE########
__FILENAME__ = _version
# This is the version of this source code.

manual_verstr = "3.0"

auto_build_num = "127"

verstr = manual_verstr + "." + auto_build_num

from distutils.version import LooseVersion as distutils_Version
__version__ = distutils_Version(verstr)

########NEW FILE########
