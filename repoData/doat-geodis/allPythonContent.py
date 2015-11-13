__FILENAME__ = city
#Copyright 2011 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

from countries import countries
from location import Location

class City(Location):
    """
    Wrapper for a city location object
    """

    #what we want to save for a city
    __spec__ = Location.__spec__ + ['country', 'state']

    #key is identical to what we want to save
    __keyspec__ = None
    
    def __init__(self, **kwargs):

        super(City, self).__init__(**kwargs)

        self.country = countries.get( kwargs.get('country', None), kwargs.get('country', '')).strip()
        self.state = kwargs.get('state', '').strip()
        

        
########NEW FILE########
__FILENAME__ = countries

countries = {
    "AD":"Andorra",
    "AE":"United Arab Emirates",
    "AF":"Afghanistan",
    "AG":"Antigua and Barbuda",
    "AI":"Anguilla",
    "AL":"Albania",
    "AM":"Armenia",
    "AN":"Netherlands Antilles",
    "AO":"Angola",
    "AQ":"Antarctica",
    "AR":"Argentina",
    "AS":"American Samoa",
    "AT":"Austria",
    "AU":"Australia",
    "AW":"Aruba",
    "AX":"Mariehamn",
    "AZ":"Azerbaijan",
    "BA":"Bosnia and Herzegovina",
    "BB":"Barbados",
    "BD":"Bangladesh",
    "BE":"Belgium",
    "BF":"Burkina Faso",
    "BG":"Bulgaria",
    "BH":"Bahrain",
    "BI":"Burundi",
    "BJ":"Benin",
    "BL":"Saint Barthelemy",
    "BM":"Bermuda",
    "BN":"Brunei",
    "BO":"Bolivia",
    "BR":"Brazil",
    "BS":"Bahamas",
    "BT":"Bhutan",
    "BV":"Bouvet Island",
    "BW":"Botswana",
    "BY":"Belarus",
    "BZ":"Belize",
    "CA":"Canada",
    "CC":"Cocos Islands",
    "CD":"Democratic Republic of the Congo",
    "CF":"Central African Republic",
    "CG":"Republic of the Congo",
    "CH":"Switzerland",
    "CI":"Ivory Coast",
    "CK":"Cook Islands",
    "CL":"Chile",
    "CM":"Cameroon",
    "CN":"China",
    "CO":"Colombia",
    "CR":"Costa Rica",
    "CU":"Cuba",
    "CV":"Cape Verde",
    "CX":"Christmas Island",
    "CY":"Cyprus",
    "CZ":"Czech Republic",
    "DE":"Germany",
    "DJ":"Djibouti",
    "DK":"Denmark",
    "DM":"Dominica",
    "DO":"Dominican Republic",
    "DZ":"Algeria",
    "EC":"Ecuador",
    "EE":"Estonia",
    "EG":"Egypt",
    "EH":"Western Sahara",
    "ER":"Eritrea",
    "ES":"Spain",
    "ET":"Ethiopia",
    "FI":"Finland",
    "FJ":"Fiji",
    "FK":"Falkland Islands",
    "FM":"Micronesia",
    "FO":"Faroe Islands",
    "FR":"France",
    "GA":"Gabon",
    "GB":"United Kingdom",
    "GD":"Grenada",
    "GE":"Georgia",
    "GF":"French Guiana",
    "GG":"Guernsey",
    "GH":"Ghana",
    "GI":"Gibraltar",
    "GL":"Greenland",
    "GM":"Gambia",
    "GN":"Guinea",
    "GP":"Guadeloupe",
    "GQ":"Equatorial Guinea",
    "GR":"Greece",
    "GS":"South Georgia and the South Sandwich Islands",
    "GT":"Guatemala",
    "GU":"Guam",
    "GW":"Guinea-Bissau",
    "GY":"Guyana",
    "HK":"Hong Kong",
    "HM":"Heard Island and McDonald Islands",
    "HN":"Honduras",
    "HR":"Croatia",
    "HT":"Haiti",
    "HU":"Hungary",
    "ID":"Indonesia",
    "IE":"Ireland",
    "IL":"Israel",
    "IM":"Isle of Man",
    "IN":"India",
    "IO":"British Indian Ocean Territory",
    "IQ":"Iraq",
    "IR":"Iran",
    "IS":"Iceland",
    "IT":"Italy",
    "JE":"Jersey",
    "JM":"Jamaica",
    "JO":"Jordan",
    "JP":"Japan",
    "KE":"Kenya",
    "KG":"Kyrgyzstan",
    "KH":"Cambodia",
    "KI":"Kiribati",
    "KM":"Comoros",
    "KN":"Saint Kitts and Nevis",
    "KP":"North Korea",
    "KR":"South Korea",
    "XK":"Kosovo",
    "KW":"Kuwait",
    "KY":"Cayman Islands",
    "KZ":"Kazakhstan",
    "LA":"Laos",
    "LB":"Lebanon",
    "LC":"Saint Lucia",
    "LI":"Liechtenstein",
    "LK":"Sri Lanka",
    "LR":"Liberia",
    "LS":"Lesotho",
    "LT":"Lithuania",
    "LU":"Luxembourg",
    "LV":"Latvia",
    "LY":"Libya",
    "MA":"Morocco",
    "MC":"Monaco",
    "MD":"Moldova",
    "ME":"Montenegro",
    "MF":"Saint Martin",
    "MG":"Madagascar",
    "MH":"Marshall Islands",
    "MK":"Macedonia",
    "ML":"Mali",
    "MM":"Myanmar",
    "MN":"Mongolia",
    "MO":"Macao",
    "MP":"Northern Mariana Islands",
    "MQ":"Martinique",
    "MR":"Mauritania",
    "MS":"Montserrat",
    "MT":"Malta",
    "MU":"Mauritius",
    "MV":"Maldives",
    "MW":"Malawi",
    "MX":"Mexico",
    "MY":"Malaysia",
    "MZ":"Mozambique",
    "NA":"Namibia",
    "NC":"New Caledonia",
    "NE":"Niger",
    "NF":"Norfolk Island",
    "NG":"Nigeria",
    "NI":"Nicaragua",
    "NL":"Netherlands",
    "NO":"Norway",
    "NP":"Nepal",
    "NR":"Nauru",
    "NU":"Niue",
    "NZ":"New Zealand",
    "OM":"Oman",
    "PA":"Panama",
    "PE":"Peru",
    "PF":"French Polynesia",
    "PG":"Papua New Guinea",
    "PH":"Philippines",
    "PK":"Pakistan",
    "PL":"Poland",
    "PM":"Saint Pierre and Miquelon",
    "PN":"Pitcairn",
    "PR":"Puerto Rico",
    "PS":"Palestinian Territory",
    "PT":"Portugal",
    "PW":"Palau",
    "PY":"Paraguay",
    "QA":"Qatar",
    "RE":"Reunion",
    "RO":"Romania",
    "RS":"Serbia",
    "RU":"Russia",
    "RW":"Rwanda",
    "SA":"Saudi Arabia",
    "SB":"Solomon Islands",
    "SC":"Seychelles",
    "SD":"Sudan",
    "SE":"Sweden",
    "SG":"Singapore",
    "SH":"Saint Helena",
    "SI":"Slovenia",
    "SJ":"Svalbard and Jan Mayen",
    "SK":"Slovakia",
    "SL":"Sierra Leone",
    "SM":"San Marino",
    "SN":"Senegal",
    "SO":"Somalia",
    "SR":"Suriname",
    "ST":"Sao Tome and Principe",
    "SV":"El Salvador",
    "SY":"Syria",
    "SZ":"Swaziland",
    "TC":"Turks and Caicos Islands",
    "TD":"Chad",
    "TF":"French Southern Territories",
    "TG":"Togo",
    "TH":"Thailand",
    "TJ":"Tajikistan",
    "TK":"Tokelau",
    "TL":"East Timor",
    "TM":"Turkmenistan",
    "TN":"Tunisia",
    "TO":"Tonga",
    "TR":"Turkey",
    "TT":"Trinidad and Tobago",
    "TV":"Tuvalu",
    "TW":"Taiwan",
    "TZ":"Tanzania",
    "UA":"Ukraine",
    "UG":"Uganda",
    "UM": "United States",
    "US":"United States",
    "UY":"Uruguay",
    "UZ":"Uzbekistan",
    "VA":"Vatican",
    "VC":"Saint Vincent and the Grenadines",
    "VE":"Venezuela",
    "VG":"British Virgin Islands",
    "VI":"U.S. Virgin Islands",
    "VN":"Vietnam",
    "VU":"Vanuatu",
    "WF":"Wallis and Futuna",
    "WS":"Samoa",
    "YE":"Yemen",
    "YT":"Mayotte",
    "ZA":"South Africa",
    "ZM":"Zambia",
    "ZW":"Zimbabwe",
    "CS":"Serbia and Montenegro"
}

########NEW FILE########
__FILENAME__ = geodis
#!/usr/bin/python

#Copyright 2011 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

import redis
import logging
import sys
from optparse import OptionParser

from provider.geonames import GeonamesImporter
from provider.ip2location import IP2LocationImporter
from provider.zipcodes import ZIPImporter
from iprange import IPRange
from city import City
from zipcode import ZIPCode

__author__="dvirsky"
__date__ ="$Mar 25, 2011 4:44:22 PM$"

redis_host = 'localhost'
redis_port = 6379
redis_db = 8

def importGeonames(fileName):
    
    global redis_host, redis_port, redis_db
    importer = GeonamesImporter(fileName, redis_host, redis_port, redis_db)
    if not importer.runImport():
        print "Could not import geonames database..."
        sys.exit(1)

    


def importIP2Location(fileName):

    print redis_host, redis_port, redis_db
    importer = IP2LocationImporter(fileName, redis_host, redis_port, redis_db)
    if not importer.runImport(True):
        print "Could not import geonames database..."
        sys.exit(1)


def importZIPCode(fileName):

    global redis_host, redis_port, redis_db
    importer = ZIPImporter(fileName, redis_host, redis_port, redis_db)
    if not importer.runImport():
        print "Could not import geonames database..."
        sys.exit(1)

    
def resolveIP(ip):
    global redis_host, redis_port, redis_db
    r = redis.Redis(host = redis_host, port = redis_port, db = redis_db)

    loc = IPRange.getZIP(ip, r)
    print loc
    

def resolveCoords(lat, lon):
    global redis_host, redis_port, redis_db
    r = redis.Redis(host = redis_host, port = redis_port, db = redis_db)
    loc = ZIPCode.getByLatLon(lat, lon, r)
    print loc


if __name__ == "__main__":
    
    logging.basicConfig(
                level = logging.INFO,
                format='%(asctime)s %(levelname)s in %(module)s.%(funcName)s (%(filename)s:%(lineno)s): %(message)s',
                )
    #build options parser
    parser = OptionParser(usage="\n\n%prog [--import_geonames | --import_ip2location] --file=FILE", version="%prog 0.1")

    parser.add_option("-g", "--import_geonames", dest="import_geonames",
                      action='store_true', default=False,
                      help='Import locations from Geonames data dump')

    parser.add_option("-i", "--import_ip2coutnry", dest="import_ip2location",
                      action='store_true', default=False,
                      help='Import ip ranges from ip2country.com dumps')
    parser.add_option("-z", "--import_zipcodes", dest="import_zipcodes",
                      action='store_true', default=False,
                      help='Import zipcodes')

    parser.add_option("-f", "--file", dest="import_file",
                  help="Location of the file we want to import", metavar="FILE")

    parser.add_option("-P", "--resolve_ip", dest="resolve_ip", default = None,
                      help="resolve an ip address to location", metavar="IP_ADDR")


    parser.add_option("-L", "--resolve_latlon", dest="resolve_latlon", default = None,
                      help="resolve an lat,lon pair into location", metavar="LAT,LON")


    parser.add_option("-H", "--redis_host", dest="redis_host", default = 'localhost',
                      help="redis host to use", metavar="HOST")

    parser.add_option("-p", "--redis_port", dest="redis_port", default = 6379,
                      type="int", help="redis port to use", metavar="PORT")

    parser.add_option("-n", "--redis_database", dest="redis_db", default = 8,
                      type="int", help="redis database to use (default 8)", metavar="DB_NUM")
    

    (options, args) = parser.parse_args()
    redis_host = options.redis_host
    redis_port = options.redis_port
    redis_db = options.redis_db
    
    if options.import_geonames:
        importGeonames(options.import_file)
        
    elif options.import_ip2location:
        importIP2Location(options.import_file)

    elif options.import_zipcodes:
        importZIPCode(options.import_file)
        
    elif options.resolve_ip:
        resolveIP(options.resolve_ip)
        
    elif options.resolve_latlon:
        coords = [float(p) for p in options.resolve_latlon.split(',')]
        resolveCoords(*coords)

    print "Success!"
    sys.exit(0)

########NEW FILE########
__FILENAME__ = iprange
#Copyright 2011 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.


import socket, struct, re
from city import City
from zipcode import ZIPCode
from geohasher import hasher
import struct

class IPRange(object):

    _indexKey = 'iprange:locations'
    def __init__(self, rangeMin, rangeMax, lat, lon, zipcode = ''):

        self.rangeMin = rangeMin
        self.rangeMax = rangeMax
        self.lat = lat
        self.lon = lon
        self.zipcode = zipcode

        #encode a numeric geohash key
        self.geoKey = hasher.encode(lat, lon)
        
        self.key = '%s:%s:%s' % (self.rangeMin, self.rangeMax, self.zipcode)

    def save(self, redisConn):
        """
        Save an IP range to redis
        @param redisConn a redis connectino or pipeline
        """
        
        redisConn.zadd(self._indexKey, '%s@%s' % (self.geoKey, self.key) , self.rangeMax)
        
        
    def __str__(self):
        """
        textual representation
        """
        return "IPRange: %s" % self.__dict__

    @staticmethod
    def get(ip, redisConn):
        """
        Get a range and all its data by ip
        """
        
        ipnum = IPRange.ip2long(ip)

        #get the location record from redis
        record = redisConn.zrangebyscore(IPRange._indexKey, ipnum ,'+inf', 0, 1, True)
        if not record:
            #not found? k!
            return None

        #extract location id
        try:
            geoKey,rng = record[0][0].split('@')
            
            lat,lon = hasher.decode(long(geoKey))
            
            rngMin, rngMax, zipcode =  rng.split(':')
            rngMin = int(rngMin)
            rngMax = int(rngMax)
        except IndexError:
            return None

        #address not in any range
        if not rngMin <= ipnum <= rngMax:
            return None
        
        return IPRange(rngMin, rngMax, lat, lon, zipcode)

    @staticmethod
    def getZIP(ip, redisConn):
        """
        Get a zipcode location object based on an IP
        will return None if you are outside the US
        """

        range = IPRange.get(ip, redisConn)
        
        if not range or not re.match('^[0-9]{5}$', range.zipcode):
            return None

        return ZIPCode.load('ZIPCode:%s' % range.zipcode, redisConn)






    @staticmethod
    def getCity(ip, redisConn):
        """
        Get location object by resolving an IP address
        @param ip IPv4 address string (e.g. 127.0.0.1)
        @oaram redisConn redis connection to the database
        @return a Location object if we can resolve this ip, else None
        """

        range = IPRange.get(ip, redisConn)
        if not range:
            return None

        

        #load a location by the
        return City.getByGeohash(hasher.encode(range.lat, range.lon), redisConn)


    @staticmethod
    def ip2long(ip):
        """
        Convert an IP string to long
        """
        ip_packed = socket.inet_aton(ip)
        return struct.unpack("!L", ip_packed)[0]
    
########NEW FILE########
__FILENAME__ = location
#Copyright 2011 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

from countries import countries
from geohasher import hasher
import math


class Location(object):
    """
    This is the base class for all location subclasses
    """
    
    __spec__ = ['lat', 'lon', 'name']
    __keyspec__ = None
    
    def __init__(self, **kwargs):

        self.lat = kwargs.get('lat', None)
        self.lon = kwargs.get('lon', None)
        self.name = kwargs.get('name', '').strip()
        

    def getId(self):

        return '%s:%s' % (self.__class__.__name__, ':'.join((str(getattr(self, x)) for x in self.__keyspec__ or self.__spec__)))

    @classmethod
    def getGeohashIndexKey(cls):

        return '%s:geohash' % cls.__name__

    def save(self, redisConn):

        
        #save all properties
        redisConn.hmset(self.getId(), dict(((k, getattr(self, k)) for k in \
                                        self.__spec__)))

        self._indexGeohash(redisConn)

        

    def _indexGeohash(self, redisConn):
        """
        Save the key of the object into the goehash index for this object type
        """

        redisConn.zadd(self.getGeohashIndexKey(), self.getId(), hasher.encode(self.lat, self.lon))


    def __str__(self):
        return "%s: %s" % (self.__class__.__name__, self.__dict__)
    
    @classmethod
    def load(cls, key, redisConn):
        """
        a Factory function to load a location from a given location key
        """
        
        d = redisConn.hgetall(str(key))
        
        if not d:
            return None
        
        #build a new object based on the loaded dict
        return cls(**d)


    @classmethod
    def getByLatLon(cls, lat, lon, redisConn):

        geoKey = hasher.encode(lat, lon)
        
        return cls.getByGeohash(geoKey, redisConn)

    @staticmethod
    def getDistance(geoHash1, geoHash2):
        """
        Estimate the distance between 2 geohashes in uint64 format
        """

#        return abs(geoHash1 - geoHash2)
        
        try:
            coords1 = hasher.decode(geoHash1)
            coords2 = hasher.decode(geoHash2)
            return math.sqrt(math.pow(coords1[0] - coords2[0], 2) +
                         math.pow(coords1[1] - coords2[1], 2))
        except Exception, e:
            print e
            return None



    @classmethod
    def getByGeohash(cls, geoKey, redisConn):
        """
        Get a location (used directly on a subclass only!) according to a geohash key
        """


        key = cls.getGeohashIndexKey()
        tx = redisConn.pipeline()
        tx.zrangebyscore(key, geoKey, 'inf', 0, 4, True)
        tx.zrevrangebyscore(key, geoKey, '-inf', 0, 4, True)
        ret = tx.execute()

        #find the two closest locations to the left and to the right of us
        candidates = filter(None, ret[0]) + filter(None, ret[1])
        
        closestDist = None
        selected = None
        if not candidates :
            return None

        for i in xrange(len(candidates)):
            
            gk = long(candidates[i][1])
            
            dist = Location.getDistance(geoKey, gk)
            if dist is None:
                continue
            
            if not closestDist or dist < closestDist:
                closestDist = dist
                selected = i
            
            
        if selected is None:
            return None

        
        return cls.load(str(candidates[selected][0]), redisConn)


        

        

        
        
        
########NEW FILE########
__FILENAME__ = geonames
#Copyright 2011 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

#Importer for locations from geonames

from city import City
import csv
import logging
import redis
import re
from importer import Importer

class GeonamesImporter(Importer):
    
    def __init__(self, fileName, redisHost, redisPort, redisDB = 0):
        """
        Init a geonames cities importer
        @param fileName path to the geonames datafile
        @param redisConn redis connection
        """

        Importer.__init__(self, fileName ,redisHost, redisPort, redisDB)

        fileNames = fileName.split(',')
        self.fileName = fileNames[0]
        self.adminCodesFileName = fileNames[1] if len(fileNames) > 1 else None
        self._adminCodes = {}
        
    def _readAdminCodes(self):
        """
        Read administrative codes for states and regions
        """

        if not self.adminCodesFileName:
            logging.warn("No admin codes file name. You won't have state names etc")
            return

        try:
            fp = open(self.adminCodesFileName)
        except Exception, e:
            logging.error("could not open file %s for reading: %s" % (self.adminCodesFileName, e))
            return

        reader = csv.reader(fp, delimiter='\t')
        for row in reader:
            
            self._adminCodes[row[0].strip()] = row[1].strip()
            

    def runImport(self):
        """
        File Format:
        5368361 Los Angeles     Los Angeles     Angelopolis,El Pueblo de Nu....     34.05223        -118.24368      P       PPL
        US              CA      037                     3694820 89      115     America/Los_Angeles     2009-11-02

        """

        self._readAdminCodes()

        try:
            fp = open(self.fileName)
        except Exception, e:
            logging.error("could not open file %s for reading: %s" % (self.fileName, e))
            return False

        reader = csv.reader(fp, delimiter='\t')
        pipe = self.redis.pipeline()

        i = 0
        for row in reader:

            try:
                name = row[2]

                country = row[8]
                adminCode = '.'.join((country, row[10]))
                region = re.sub('\\(.+\\)', '', self._adminCodes.get(adminCode, '')).strip()

                #for us states - take only state code not full name
                if country == 'US':
                    region = row[10]

                lat = float(row[4])
                lon = float(row[5])

                loc = City(name = name,
                                country = country,
                                state = region,
                                lat = lat,
                                lon = lon)

                loc.save(pipe)


                
            except Exception, e:
                logging.error("Could not import line %s: %s" % (row, e))
            i += 1
            if i % 1000 == 0:
                pipe.execute()
        pipe.execute()

        logging.info("Imported %d locations" % i)

        return True
########NEW FILE########
__FILENAME__ = importer
#Copyright 2011 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

import redis

class Importer(object):
    """
    Base class for all importer scripts, inits a redis connection and file name
    """
    def __init__(self, fileName ,redisHost, redisPort, redisDB):

        self.fileName = fileName
        self.redis = redis.Redis(host = redisHost, port = redisPort, db = redisDB)

        

########NEW FILE########
__FILENAME__ = ip2location
#Copyright 2011 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

#Importer for locations from ip2location.com databases


import csv
import logging
import redis

from importer import Importer
from iprange import IPRange

class IP2LocationImporter(Importer):

    def runImport(self, reset = False):
        """
        File Format:
        "67134976","67135231","US","UNITED STATES","CALIFORNIA","LOS ANGELES","34.045200","-118.284000","90001"

        """
        if reset:
            print "Deleting old ip data..."
            self.redis.delete(IPRange._indexKey)

        print "Starting import..."
            
        try:
            fp = open(self.fileName)
        except Exception, e:
            logging.error("could not open file %s for reading: %s" % (self.fileName, e))
            return False

        reader = csv.reader(fp, delimiter=',', quotechar='"')
        pipe = self.redis.pipeline()

        i = 0
        for row in reader:
            
            try:
                #parse the row
                countryCode = row[3]
                rangeMin = int(row[0])
                rangeMax = int(row[1])
                lat = float(row[6])
                lon = float(row[7])

                #take the zipcode if possible
                try:
                    zipcode = row[8]
                except:
                    zipcode = ''


                #junk record
                if countryCode == '-' and (not lat and not lon):
                    continue
                    
                range = IPRange(rangeMin, rangeMax, lat, lon, zipcode)
                range.save(pipe)
                
            except Exception, e:
                logging.error("Could not save record: %s" % e)

            i += 1
            if i % 10000 == 0:
                logging.info("Dumping pipe. did %d ranges" % i)
                pipe.execute()

        pipe.execute()
        logging.info("Imported %d locations" % i)

        return i

            
########NEW FILE########
__FILENAME__ = zipcodes
#Copyright 2011 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

#Importer for zipcodes.csv file found in /data

from zipcode import ZIPCode
from us_states import code_to_state
import csv
import logging

from importer import Importer

class ZIPImporter(Importer):
    
        
    def runImport(self):
        """
        File Format:
        "00210","Portsmouth","NH","43.005895","-71.013202","-5","1"
        """

        try:
            fp = open(self.fileName)
        except Exception, e:
            logging.error("could not open file %s for reading: %s" % (self.fileName, e))
            return False

        reader = csv.reader(fp, delimiter=',', quotechar = '"')
        pipe = self.redis.pipeline()

        i = 0
        for row in reader:

            try:
                name = row[0]
                city = row[1]
                stateCode = row[2]
                lat = float(row[3])
                lon = float(row[4])
                state = stateCode#code_to_state.get(stateCode, '').title()
                country = 'US'

                loc = ZIPCode(name = name,
                              city = city,
                                country = country,
                                state = state,
                                lat = lat,
                                lon = lon)

                loc.save(pipe)

                
                
            except Exception, e:
                logging.error("Could not import line %s: %s" % (row, e))
            i += 1
            if i % 1000 == 0:
                pipe.execute()

        pipe.execute()

        logging.info("Imported %d locations" % i)

        return i

########NEW FILE########
__FILENAME__ = us_states
#US State codes taken from http://www.cmmichael.com/blog/2006/12/29/state-code-mappings-for-python

state_to_code = {'VERMONT': 'VT', 'GEORGIA': 'GA', 'IOWA': 'IA', 'Armed Forces Pacific': 'AP', 'GUAM': 'GU', 'KANSAS': 'KS', 'FLORIDA': 'FL', 'AMERICAN SAMOA': 'AS', 'NORTH CAROLINA': 'NC', 'HAWAII': 'HI', 'NEW YORK': 'NY', 'CALIFORNIA': 'CA', 'ALABAMA': 'AL', 'IDAHO': 'ID', 'FEDERATED STATES OF MICRONESIA': 'FM', 'Armed Forces Americas': 'AA', 'DELAWARE': 'DE', 'ALASKA': 'AK', 'ILLINOIS': 'IL', 'Armed Forces Africa': 'AE', 'SOUTH DAKOTA': 'SD', 'CONNECTICUT': 'CT', 'MONTANA': 'MT', 'MASSACHUSETTS': 'MA', 'PUERTO RICO': 'PR', 'Armed Forces Canada': 'AE', 'NEW HAMPSHIRE': 'NH', 'MARYLAND': 'MD', 'NEW MEXICO': 'NM', 'MISSISSIPPI': 'MS', 'TENNESSEE': 'TN', 'PALAU': 'PW', 'COLORADO': 'CO', 'Armed Forces Middle East': 'AE', 'NEW JERSEY': 'NJ', 'UTAH': 'UT', 'MICHIGAN': 'MI', 'WEST VIRGINIA': 'WV', 'WASHINGTON': 'WA', 'MINNESOTA': 'MN', 'OREGON': 'OR', 'VIRGINIA': 'VA', 'VIRGIN ISLANDS': 'VI', 'MARSHALL ISLANDS': 'MH', 'WYOMING': 'WY', 'OHIO': 'OH', 'SOUTH CAROLINA': 'SC', 'INDIANA': 'IN', 'NEVADA': 'NV', 'LOUISIANA': 'LA', 'NORTHERN MARIANA ISLANDS': 'MP', 'NEBRASKA': 'NE', 'ARIZONA': 'AZ', 'WISCONSIN': 'WI', 'NORTH DAKOTA': 'ND', 'Armed Forces Europe': 'AE', 'PENNSYLVANIA': 'PA', 'OKLAHOMA': 'OK', 'KENTUCKY': 'KY', 'RHODE ISLAND': 'RI', 'DISTRICT OF COLUMBIA': 'DC', 'ARKANSAS': 'AR', 'MISSOURI': 'MO', 'TEXAS': 'TX', 'MAINE': 'ME'}

code_to_state = {'WA': 'WASHINGTON', 'VA': 'VIRGINIA', 'DE': 'DELAWARE', 'DC': 'DISTRICT OF COLUMBIA', 'WI': 'WISCONSIN', 'WV': 'WEST VIRGINIA', 'HI': 'HAWAII', 'AE': 'Armed Forces Middle East', 'FL': 'FLORIDA', 'FM': 'FEDERATED STATES OF MICRONESIA', 'WY': 'WYOMING', 'NH': 'NEW HAMPSHIRE', 'NJ': 'NEW JERSEY', 'NM': 'NEW MEXICO', 'TX': 'TEXAS', 'LA': 'LOUISIANA', 'NC': 'NORTH CAROLINA', 'ND': 'NORTH DAKOTA', 'NE': 'NEBRASKA', 'TN': 'TENNESSEE', 'NY': 'NEW YORK', 'PA': 'PENNSYLVANIA', 'CA': 'CALIFORNIA', 'NV': 'NEVADA', 'AA': 'Armed Forces Americas', 'PW': 'PALAU', 'GU': 'GUAM', 'CO': 'COLORADO', 'VI': 'VIRGIN ISLANDS', 'AK': 'ALASKA', 'AL': 'ALABAMA', 'AP': 'Armed Forces Pacific', 'AS': 'AMERICAN SAMOA', 'AR': 'ARKANSAS', 'VT': 'VERMONT', 'IL': 'ILLINOIS', 'GA': 'GEORGIA', 'IN': 'INDIANA', 'IA': 'IOWA', 'OK': 'OKLAHOMA', 'AZ': 'ARIZONA', 'ID': 'IDAHO', 'CT': 'CONNECTICUT', 'ME': 'MAINE', 'MD': 'MARYLAND', 'MA': 'MASSACHUSETTS', 'OH': 'OHIO', 'UT': 'UTAH', 'MO': 'MISSOURI', 'MN': 'MINNESOTA', 'MI': 'MICHIGAN', 'MH': 'MARSHALL ISLANDS', 'RI': 'RHODE ISLAND', 'KS': 'KANSAS', 'MT': 'MONTANA', 'MP': 'NORTHERN MARIANA ISLANDS', 'MS': 'MISSISSIPPI', 'PR': 'PUERTO RICO', 'SC': 'SOUTH CAROLINA', 'KY': 'KENTUCKY', 'OR': 'OREGON', 'SD': 'SOUTH DAKOTA'}

########NEW FILE########
__FILENAME__ = zipcode
#Copyright 2011 Do@. All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are
#permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this list of
#      conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this list
#      of conditions and the following disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY Do@ ``AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#The views and conclusions contained in the software and documentation are those of the
#authors and should not be interpreted as representing official policies, either expressed
#or implied, of Do@.

from countries import countries

from location import Location

class ZIPCode(Location):

    __spec__ = Location.__spec__ + ['country', 'state', 'city']
    __keyspec__ = ['name']
    
    def __init__(self, **kwargs):

        super(ZIPCode, self).__init__(**kwargs)

        self.country = countries.get( kwargs.get('country', None), kwargs.get('country', '')).strip()
        self.state = kwargs.get('state', '').strip()
        self.city = kwargs.get('city', '').strip()
        

    
########NEW FILE########
__FILENAME__ = benchmark
#performance benchmarks

import sys
import os
import redis
from iprange import IPRange
from city import City
import time

def benchResolveIPs(num):
    ips = ['209.85.238.11',
    '209.85.238.4',
    '216.239.33.96',
    '216.239.33.97',
    '216.239.33.98',
    '216.239.33.99',
    '216.239.37.98',
    '216.239.37.99',
    '216.239.39.98',
    '216.239.39.99',
    '216.239.41.96',
    '216.239.41.97',
    '216.239.41.98',
    '216.239.41.99',
    '216.239.45.4',
    '216.239.51.96',
    '216.239.51.97',
    '216.239.51.98',
    '216.239.51.99',
    '216.239.53.98',
    '216.239.53.99',
    '216.239.57.96',
    '216.239.57.97',
    '216.239.57.98',
    '216.239.57.99',
    '216.239.59.98',
    '216.239.59.99',
    '216.33.229.163',
    '64.233.173.193',
    '64.233.173.194',
    '64.233.173.195',
    '64.233.173.196',
    '64.233.173.197',
    '64.233.173.198',
    '64.233.173.199',
    '64.233.173.200',
    '64.233.173.201',
    '64.233.173.202',
    '64.233.173.203',
    '64.233.173.204',
    '64.233.173.205',
    '64.233.173.206',
    '64.233.173.207',
    '64.233.173.208',
    '64.233.173.209',
    '64.233.173.210',
    '64.233.173.211',
    '64.233.173.212',
    '64.233.173.213',
    '64.233.173.214',
    '64.233.173.215',
    '64.233.173.216',
    '64.233.173.217',
    '64.233.173.218',
    '64.233.173.219',
    '64.233.173.220',
    '64.233.173.221',
    '64.233.173.222',
    '64.233.173.223',
    '64.233.173.224',
    '64.233.173.225',
    '64.233.173.226',
    '64.233.173.227',
    '64.233.173.228',
    '64.233.173.229',
    '64.233.173.230',
    '64.233.173.231',
    '64.233.173.232',
    '64.233.173.233',
    '64.233.173.234',
    '64.233.173.235',
    '64.233.173.236',
    '64.233.173.237',
    '64.233.173.238',
    '64.233.173.239',
    '64.233.173.240',
    '64.233.173.241',
    '64.233.173.242',
    '64.233.173.243',
    '64.233.173.244',
    '64.233.173.245',
    '64.233.173.246',
    '64.233.173.247',
    '64.233.173.248',
    '64.233.173.249',
    '64.233.173.250',
    '64.233.173.251',
    '64.233.173.252',
    '64.233.173.253',
    '64.233.173.254',
    '64.233.173.255',
    '64.68.90.1',
    '64.68.90.10',
    '64.68.90.11',
    '64.68.90.12',
    '64.68.90.129',
    '64.68.90.13',
    '64.68.90.130',
    '64.68.90.131',
    '64.68.90.132',
    '64.68.90.133',
    '64.68.90.134',
    '64.68.90.135',
    '64.68.90.136',
    '64.68.90.137',
    '64.68.90.138',
    '64.68.90.139',
    '64.68.90.14',
    '64.68.90.140',
    '64.68.90.141',
    '64.68.90.142',
    '64.68.90.143',
    '64.68.90.144',
    '64.68.90.145',
    '64.68.90.146',
    '64.68.90.147',
    '64.68.90.148',
    '64.68.90.149',
    '64.68.90.15',
    '64.68.90.150',
    '64.68.90.151',
    '64.68.90.152',
    '64.68.90.153',
    '64.68.90.154',
    '64.68.90.155',
    '64.68.90.156',
    '64.68.90.157',
    '64.68.90.158',
    '64.68.90.159',
    '64.68.90.16',
    '64.68.90.160',
    '64.68.90.161',
    '64.68.90.162',
    '64.68.90.163',
    '64.68.90.164',
    '64.68.90.165',
    '64.68.90.166',
    '64.68.90.167',
    '64.68.90.168',
    '64.68.90.169',
    '64.68.90.17',
    '64.68.90.170',
    '64.68.90.171',
    '64.68.90.172',
    '64.68.90.173',
    '64.68.90.174',
    '64.68.90.175',
    '64.68.90.176',
    '64.68.90.177',
    '64.68.90.178',
    '64.68.90.179',
    '64.68.90.18',
    '64.68.90.180',
    '64.68.90.181',
    '64.68.90.182',
    '64.68.90.183',
    '64.68.90.184',
    '64.68.90.185',
    '64.68.90.186',
    '64.68.90.187',
    '64.68.90.188',
    '64.68.90.189',
    '64.68.90.19',
    '64.68.90.190',
    '64.68.90.191',
    '64.68.90.192',
    '64.68.90.193',
    '64.68.90.194',
    '64.68.90.195',
    '64.68.90.196',
    '64.68.90.197',
    '64.68.90.198',
    '64.68.90.199',
    '64.68.90.2',
    '64.68.90.20',
    '64.68.90.200',
    '64.68.90.201',
    '64.68.90.202',
    '64.68.90.203',
    '64.68.90.204',
    '64.68.90.205',
    '64.68.90.206',
    '64.68.90.207',
    '64.68.90.208',
    '64.68.90.21',
    '64.68.90.22',
    '64.68.90.23',
    '64.68.90.24',
    '64.68.90.25',
    '64.68.90.26',
    '64.68.90.27',
    '64.68.90.28',
    '64.68.90.29',
    '64.68.90.3',
    '64.68.90.30',
    '64.68.90.31',
    '64.68.90.32',
    '64.68.90.33',
    '64.68.90.34',
    '64.68.90.35',
    '64.68.90.36',
    '64.68.90.37',
    '64.68.90.38',
    '64.68.90.39',
    '64.68.90.4',
    '64.68.90.40',
    '64.68.90.41',
    '64.68.90.42',
    '64.68.90.43',
    '64.68.90.44',
    '64.68.90.45',
    '64.68.90.46',
    '64.68.90.47',
    '64.68.90.48',
    '64.68.90.49',
    '64.68.90.5',
    '64.68.90.50',
    '64.68.90.51',
    '64.68.90.52',
    '64.68.90.53',
    '64.68.90.54',
    '64.68.90.55',
    '64.68.90.56',
    '64.68.90.57',
    '64.68.90.58',
    '64.68.90.59',
    '64.68.90.6',
    '64.68.90.60',
    '64.68.90.61',
    '64.68.90.62',
    '64.68.90.63',
    '64.68.90.64',
    '64.68.90.65',
    '64.68.90.66',
    '64.68.90.67',
    '64.68.90.68',
    '64.68.90.69',
    '64.68.90.7',
    '64.68.90.70',
    '64.68.90.71',
    '64.68.90.72',
    '64.68.90.73',
    '64.68.90.74',
    '64.68.90.75',
    '64.68.90.76',
    '64.68.90.77',
    '64.68.90.78',
    '64.68.90.79',
    '64.68.90.8',
    '64.68.90.80',
    '64.68.90.9']

    #ips = ['166.205.138.92', '62.0.18.221',  '69.147.125.65', '188.127.241.156', '79.178.26.33']
    r = redis.Redis()
    nips = len(ips)
    for i in xrange(num):
        ip = ips[i % nips]
        loc = IPRange.getCity(ip, r)
        
    return num

def benchResolveCoords(num):

    coords = [(-3.03333,53.47778), (40.7226,-74.66544), (31.78199,35.2196), (0,0),(45,45)]
    r = redis.Redis()
    ncoords = len(coords)
    for i in xrange(num):
        lat,lon = coords[i % ncoords]
        loc = City.getByLatLon(lat,lon, r)
        

    return num

def benchSingleProc(func, num):

    print "Running benchmark %s for %d times..." % (func.__name__, num)
    st = time.time()
    num = func(num)
    et = time.time()

    print "time: %.03fsec, rate: %.03fq/s" % (et - st, (float(num) / (et-st)))
    
if __name__ == "__main__":


   benchSingleProc(benchResolveCoords, 10000)
   benchSingleProc(benchResolveIPs, 10000)
########NEW FILE########
__FILENAME__ = testGeodis
import sys,os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../src')
import unittest
import redis
from provider.geonames import GeonamesImporter
from provider.ip2location import IP2LocationImporter
from provider.zipcodes import ZIPImporter


from city import City
from iprange import IPRange
from zipcode import ZIPCode

class  TestProvidersTestCase(unittest.TestCase):
    def setUp(self):
        self.redisHost = 'localhost'
        self.redisPort = 6379
        self.redisDB = 8
    
    def test1_ImportGeonames(self):

        importer = GeonamesImporter('./data/locations.csv', self.redisHost, self.redisPort, self.redisDB)
        self.assertTrue(importer.runImport() > 0, 'Could not import cities csv')

        

    def test2_ImportIP2Location(self):

        importer = IP2LocationImporter('./data/ip2location.csv', self.redisHost, self.redisPort, self.redisDB)
        self.assertTrue(importer.runImport() > 0, 'Could not import ip ranges csv')


    def test3_ImportZIP(self):

        importer = ZIPImporter('./data/zipcodes.csv', self.redisHost, self.redisPort, self.redisDB)
        self.assertTrue(importer.runImport() > 0, 'Could not import zipcodes csv')

    def test4_resolve(self):
        r = redis.Redis(self.redisHost, self.redisPort, self.redisDB)
        #resolve by coords
        
        loc = City.getByLatLon(34.05223, -118.24368, r)
        
        self.assertTrue(loc is not None)
        self.assertTrue(loc.country == 'United States')
        self.assertTrue(loc.state == 'CA' or loc.state == 'California')
        
        #resolve by ip
        ip = '4.3.68.1'

        loc = IPRange.getCity(ip, r)
        
        self.assertTrue(loc is not None)
        self.assertTrue(loc.country == 'United States')
        self.assertTrue(loc.state == 'CA' or loc.state == 'California')

        #resolve zip by lat,lon
        loc = ZIPCode.getByLatLon(34.0452, -118.284, r)
        
        self.assertTrue(loc is not None)
        self.assertTrue(loc.name == '90006')
        self.assertTrue(loc.country == 'United States')
        self.assertTrue(loc.state == 'CA' or loc.state == 'California')

        #resolve zip bu ip
        loc = IPRange.getZIP(ip, r)
        self.assertTrue(loc is not None)
        self.assertTrue(loc.name == '90001')
        self.assertTrue(loc.country == 'United States')
        self.assertTrue(loc.state == 'CA' or loc.state == 'California')
        

        
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
