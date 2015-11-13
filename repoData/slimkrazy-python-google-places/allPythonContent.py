__FILENAME__ = lang
"""
Valid languages to be used in Google Places API calls.

@author: sam@slimkrazy.com
"""

ARABIC = 'ar'
BASQUE = 'eu'
BULGARIAN = 'bg'
BENGALI = 'bn'
CATALAN = 'ca'
CZECH ='cs'
DANISH ='da'
GERMAN = 'de'
GREEK = 'el'
ENGLISH = 'en'
ENGLISH_AUSTRALIAN = 'en-AU'
ENGLISH_GREAT_BRITAIN = 'en-GB'
SPANISH = 'es'
FARSI = 'fa'
FINNISH = 'fi'
FILIPINO = 'fil'
FRENCH ='fr'
GALICAIN = 'gl'
GUJURATI = 'gu'
HINDI ='hi'
CROATIAN ='hr'
HUNGARIAN ='hu'
INDONESIAN ='id'
ITALIAN = 'it'
HEBREW = 'iw'
JAPANESE = 'ja'
KANNADA = 'kn'
KOREAN = 'ko'
LITHUANIAN = 'lt'
LATVIAN = 'lv'
MALAYALAM = 'ml'
MARATHI = 'mr'
DUTCH = 'nl'
NORWEGIAN_NYNORSK = 'nn'
NORWEGIAN = 'no'
ORIYA = 'or'
POLISH = 'pl'
PORTUGUESE = 'pt'
PORTUGUESE_BRAZIL = 'pt=BR'
PORTUGUESE_PORTUGAL = 'pt-PT'
ROMANSCH = 'rm'
ROMANIAN = 'ro'
RUSSIAN = 'ru'
SLOVAK = 'sk'
SLOVENIAN = 'sl'
SERBIAN = 'sr'
SWEDISH = 'sv'
TAGALOG = 'tl'
TAMIL ='ta'
TELUGU = 'te'
THAI = 'th'
TURKISH = 'tr'
UKRANIAN = 'uk'
VIETNAMESE = 'vi'
CHINESE_SIMPLIFIED = 'zh-CN'
CHINESE_TRADITIONAL = 'zh-TW'

########NEW FILE########
__FILENAME__ = ranking
"""
Valid place search rankings to be optionally used in Google Place query
api calls.

@author: sam@slimkrazy.com
"""

DISTANCE = 'distance'
PROMINENCE = 'prominence'

########NEW FILE########
__FILENAME__ = testfixtures
"""
Sample JSON responses pulled from Google Places API.

"""

PLACES_QUERY_RESPONSE = {
   "html_attributions" : [
      "Listings by \u003ca href=\"http://www.yellowpages.com.au/\"\u003eYellow Pages\u003c/a\u003e"
   ],
   "results" : [
      {
         "geometry" : {
            "location" : {
               "lat" : -33.8719830,
               "lng" : 151.1990860
            }
         },
         "icon" : "http://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
         "id" : "677679492a58049a7eae079e0890897eb953d79b",
         "name" : "Zaaffran Restaurant - BBQ and GRILL, Darling Harbour",
         "rating" : 3.90,
         "reference" : "CpQBjAAAAFAOaZhKjoDYfDsnISY6p4DKgdtrXTLJBhYsF0WnLBrkLHN3LdLpxc9VsbQKfbtg87nnDsl-SdCKT60Vs4Sxe_lCNCgRBxgq0JBBj8maNZ9pEp_LWjq8O-shdjh-LexdN5o-ZYLVBXhqX2az4TFvuOqme0eRirqMyatKgfn9nuKEkKR2a5tfFQlMfSZSlbyoOxIQVffhpcBqaua-_Yb364wx9xoUC1I-81Wj7aBmSmkctXv_YE7jqgQ",
         "types" : [ "restaurant", "food", "establishment" ],
         "vicinity" : "Harbourside Centre 10 Darling Drive, Darling Harbour, Sydney"
      },
      {
         "geometry" : {
            "location" : {
               "lat" : -33.8721970,
               "lng" : 151.1987820
            }
         },
         "icon" : "http://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
         "id" : "27ea39c8fed1c0437069066b8dccf958a2d06f19",
         "name" : "Criniti's",
         "rating" : 3.10,
         "reference" : "CmRgAAAAm4ajUz0FWaV2gB5mBbdIFhg-Jn98p1AQOrr1QxUWh7Q0nhEUhZL-hY9L4l5ifvRfGttf_gyBpSsGaxMjnr_pcPGUIQKES0vScLQpwM7jsS3BQKB83G9B_SlJFcRuD5dDEhCoNxepsgfJ5YSuXlYjVo9tGhQaKigmZ0WQul__A702AiH3WIy6-A",
         "types" : [ "restaurant", "food", "establishment" ],
         "vicinity" : "231/10 Darling Dr, DARLING HARBOUR"
      },
      {
         "geometry" : {
            "location" : {
               "lat" : -33.8720340,
               "lng" : 151.198540
            }
         },
         "icon" : "http://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
         "id" : "cb853832ab8368db3adc52c657fe063dac0f3b11",
         "name" : "Al Ponte Harbour View Restaurant",
         "reference" : "CoQBeAAAAMQ4yYBquhcHj8qzcgUNdwgeiIOhh-Eyf21y9J58y9JXVO7yzw1mFd_wKKjEYJLR_PPjbPRGJEDFnR6eCK_zw1qwrzdyxjnM2zwvdiJ-MLwt3PxVvkkPAjLJYp1cerBc0KTyUVfBo7B4U7RFt4r3DueQ4mz6N-6G7CBoddtfRnm5EhCSGc8yi1k4EQ8whHhKfzxpGhTA1mKVV8kydhqLCsbWDitFMxqzvA",
         "types" : [ "restaurant", "food", "establishment" ],
         "vicinity" : "10 Darling Dr, Sydney CBD"
      },
      {
         "geometry" : {
            "location" : {
               "lat" : -33.8711490,
               "lng" : 151.1985180
            }
         },
         "icon" : "http://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
         "id" : "400d8b4ee30d39175f69fddfcc50590860e59d62",
         "name" : "JB's Bar at Holiday Inn Darling Harbour",
         "reference" : "CoQBfgAAACn9RQ5w_BCAcdF14KQjTh_youPZUA5a7Fbbc74gu3gWaGkl78jlDnIYuUCNOEBs4Up-iw_KrHHDRx58A91Pwqnhrf5RSMihz5gAj3M7X7IW8a_Qxl7-MuAbkoNd6rTbHXtTTWtFtKAhQBljsHPahn0kDPXXSwrhn3WjSfFQX6FfEhCWPSB0ISfYioqpCBWFveZlGhSdW7eYv0NUEAtgTAzJ7x0r4NDHPQ",
         "types" : [ "restaurant", "food", "establishment" ],
         "vicinity" : "Furama Hotel, 68 Harbour Street, Darling Harbour, Sydney"
      },
      {
         "geometry" : {
            "location" : {
               "lat" : -33.8711490,
               "lng" : 151.1985180
            }
         },
         "icon" : "http://maps.gstatic.com/mapfiles/place_api/icons/generic_business-71.png",
         "id" : "f12a10b450db59528c18e57dea9f56f88c65c2fa",
         "name" : "Health Harbour",
         "reference" : "CnRlAAAA97YiSpT9ArwBWRZ_7FeddhMtQ4rGTy9v277_B4Y3jxUFKkZVczf3YHrhSLGuKugNQQpCDMWjYKv6LkSA8CiECzh5z7B2wOMkhn0PGjpq01p0QRapJuA6z9pQFS_oTeUq0M_paSCQ_GEB8A5-PpkJXxIQHAuoj0nyrgNwjLtByDHAgBoUdHaA6D2ceLp8ga5IJqxfqOnOwS4",
         "types" : [ "food", "store", "establishment" ],
         "vicinity" : "Darling Harbour"
      }
   ],
   "status" : "OK"
}

########NEW FILE########
__FILENAME__ = tests
"""
Unit tests for google places.

@author: sam@slimkrazy.com
"""

from random import randint
import unittest

from googleplaces import GooglePlaces, GooglePlacesSearchResult
from testfixtures import PLACES_QUERY_RESPONSE

DUMMY_API_KEY = 'foobarbaz'


class Test(unittest.TestCase):

    def setUp(self):
        self._places_instance = GooglePlaces(DUMMY_API_KEY)

    def tearDown(self):
        self._places_instance = None


    def testSuccessfulResponse(self):
        query_result = GooglePlacesSearchResult(
                self._places_instance,
                PLACES_QUERY_RESPONSE)
        self.assertEqual(5, len(query_result.places),
                         'Place count is incorrect.')
        place_index = randint(0, len(query_result.places))
        place = query_result.places[place_index]
        response_place_entity = PLACES_QUERY_RESPONSE['results'][place_index]
        self.assertEqual(place.id, response_place_entity.get('id'),
                         'ID value is incorrect.')
        self.assertEqual(
                         place.reference,
                         response_place_entity.get('reference'),
                         'Reference value is incorrect.')
        self.assertEqual(place.name, response_place_entity.get('name'),
                         'Name value is incorrect.')
        self.assertEqual(place.vicinity, response_place_entity.get('vicinity'),
                         'Vicinity value is incorrect.')
        self.assertEqual(
                place.geo_location,
                response_place_entity['geometry']['location'],
                'Geo-location value is incorrect.')
        self.assertEqual(place.rating, response_place_entity.get('rating'),
                         'Rating value is incorrect.')
        #TODO: Testing of data pulled by the details API - Requires mocking.


if __name__ == "__main__":
    unittest.main()
########NEW FILE########
__FILENAME__ = types
"""
Valid types to be optionally used in Google Place query api calls.

@author: sam@slimkrazy.com
"""

TYPE_ACCOUNTING = 'accounting'
TYPE_AIRPORT = 'airport'
TYPE_AMUSEMENT_PARK = 'amusement_park'
TYPE_AQUARIUM = 'aquarium'
TYPE_ART_GALLERY = 'art_gallery'
TYPE_ATM = 'atm'
TYPE_BAKERY = 'bakery'
TYPE_BANK = 'bank'
TYPE_BAR = 'bar'
TYPE_BEAUTY_SALON = 'beauty_salon'
TYPE_BICYCLE_STORE = 'bicycle_store'
TYPE_BOOK_STORE = 'book_store'
TYPE_BOWLING_ALLEY = 'bowling_alley'
TYPE_BUS_STATION = 'bus_station'
TYPE_CAFE = 'cafe'
TYPE_CAMPGROUND = 'campground'
TYPE_CAR_DEALER = 'car_dealer'
TYPE_CAR_RENTAL = 'car_rental'
TYPE_CAR_REPAIR = 'car_repair'
TYPE_CAR_WASH = 'car_wash'
TYPE_CASINO = 'casino'
TYPE_CEMETERY = 'cemetery'
TYPE_CHURCH = 'church'
TYPE_CITY_HALL = 'city_hall'
TYPE_CLOTHING_STORE = 'clothing_store'
TYPE_CONVENIENCE_STORE = 'convenience_store'
TYPE_COURTHOUSE = 'courthouse'
TYPE_DENTIST = 'dentist'
TYPE_DEPARTMENT_STORE = 'department_store'
TYPE_DOCTOR = 'doctor'
TYPE_ELECTRICIAN = 'electrician'
TYPE_ELECTRONICS_STORE = 'electronics_store'
TYPE_EMBASSY = 'embassy'
TYPE_ESTABLISHMENT = 'establishment'
TYPE_FINANCE = 'finance'
TYPE_FIRE_STATION = 'fire_station'
TYPE_FLORIST = 'florist'
TYPE_FOOD = 'food'
TYPE_FUNERAL_HOME = 'funeral_home'
TYPE_FURNITURE_STORE = 'furniture_store'
TYPE_GAS_STATION = 'gas_station'
TYPE_GENERAL_CONTRACTOR = 'general_contractor'
TYPE_GEOCODE = 'geocode'
TYPE_GROCERY_OR_SUPERMARKET = 'grocery_or_supermarket'
TYPE_GYM = 'gym'
TYPE_HAIR_CARE = 'hair_care'
TYPE_HARDWARE_STORE = 'hardware_store'
TYPE_HEALTH = 'health'
TYPE_HINDU_TEMPLE = 'hindu_temple'
TYPE_HOME_GOODS_STORE = 'home_goods_store'
TYPE_HOSPITAL = 'hospital'
TYPE_INSURANCE_AGENCY = 'insurance_agency'
TYPE_JEWELRY_STORE = 'jewelry_store'
TYPE_LAUNDRY = 'laundry'
TYPE_LAWYER = 'lawyer'
TYPE_LIBRARY = 'library'
TYPE_LIQUOR_STORE = 'liquor_store'
TYPE_LOCAL_GOVERNMENT_OFFICE = 'local_government_office'
TYPE_LOCKSMITH = 'locksmith'
TYPE_LODGING = 'lodging'
TYPE_MEAL_DELIVERY = 'meal_delivery'
TYPE_MEAL_TAKEAWAY = 'meal_takeaway'
TYPE_MOSQUE = 'mosque'
TYPE_MOVIE_RENTAL = 'movie_rental'
TYPE_MOVIE_THEATER = 'movie_theater'
TYPE_MOVING_COMPANY = 'moving_company'
TYPE_MUSEUM = 'museum'
TYPE_NIGHT_CLUB = 'night_club'
TYPE_PAINTER = 'painter'
TYPE_PARK = 'park'
TYPE_PARKING = 'parking'
TYPE_PET_STORE = 'pet_store'
TYPE_PHARMACY = 'pharmacy'
TYPE_PHYSIOTHERAPIST = 'physiotherapist'
TYPE_PLACE_OF_WORSHIP = 'place_of_worship'
TYPE_PLUMBER = 'plumber'
TYPE_POLICE = 'police'
TYPE_POST_OFFICE = 'post_office'
TYPE_REAL_ESTATE_AGENCY = 'real_estate_agency'
TYPE_RESTAURANT = 'restaurant'
TYPE_ROOFING_CONTRACTOR = 'roofing_contractor'
TYPE_RV_PARK = 'rv_park'
TYPE_SCHOOL = 'school'
TYPE_SHOE_STORE = 'shoe_store'
TYPE_SHOPPING_MALL = 'shopping_mall'
TYPE_SPA = 'spa'
TYPE_STADIUM = 'stadium'
TYPE_STORAGE = 'storage'
TYPE_STORE = 'store'
TYPE_SUBWAY_STATION = 'subway_station'
TYPE_SYNAGOGUE = 'synagogue'
TYPE_TAXI_STAND = 'taxi_stand'
TYPE_TRAIN_STATION = 'train_station'
TYPE_TRAVEL_AGENCY = 'travel_agency'
TYPE_UNIVERSITY = 'university'
TYPE_VETERINARY_CARE = 'veterinary_care'
TYPE_ZOO = 'zoo'

# The following types supported by the Places API when sending
# Place Search requests. These types cannot be used when adding a new Place.

TYPE_ADMINISTRATIVE_AREA_LEVEL_1 = 'administrative_area_level_1'
TYPE_ADMINISTRATIVE_AREA_LEVEL_2 = 'administrative_area_level_2'
TYPE_ADMINISTRATIVE_AREA_LEVEL_3 = 'administrative_area_level_3'
TYPE_COLLOQUIAL_AREA = 'colloquial_area'
TYPE_COUNTRY = 'country'
TYPE_FLOOR = 'floor'
TYPE_INTERSECTION = 'intersection'
TYPE_LOCALITY = 'locality'
TYPE_NATURAL_FEATURE = 'natural_feature'
TYPE_NEIGHBORHOOD = 'neighborhood'
TYPE_POLITICAL = 'political'
TYPE_POINT_OF_INTEREST = 'point_of_interest'
TYPE_POST_BOX = 'post_box'
TYPE_POSTAL_CODE = 'postal_code'
TYPE_POSTAL_CODE_PREFIX = 'postal_code_prefix'
TYPE_POSTAL_TOWN = 'postal_town'
TYPE_PREMISE = 'premise'
TYPE_ROOM = 'room'
TYPE_ROUTE = 'route'
TYPE_STREET_ADDRESS = 'street_address'
TYPE_STREET_NUMBER = 'street_number'
TYPE_SUBLOCALITY = 'sublocality'
TYPE_SUBLOCALITY_LEVEL_4 = 'sublocality_level_4'
TYPE_SUBLOCALITY_LEVEL_5 = 'sublocality_level_5'
TYPE_SUBLOCALITY_LEVEL_3 = 'sublocality_level_3'
TYPE_SUBLOCALITY_LEVEL_2 = 'sublocality_level_2'
TYPE_SUBLOCALITY_LEVEL_1 = 'sublocality_level_1'
TYPE_SUBPREMISE = 'subpremise'
TYPE_TRANSIT_STATION = 'transit_station'

########NEW FILE########
