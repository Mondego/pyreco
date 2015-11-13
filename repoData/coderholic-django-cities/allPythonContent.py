__FILENAME__ = admin
from django.contrib import admin
from models import *

class CitiesAdmin(admin.ModelAdmin):
    raw_id_fields = ['alt_names']

class CountryAdmin(CitiesAdmin):
    list_display = ['name', 'code', 'code3', 'tld', 'phone', 'continent', 'area', 'population']
    search_fields = ['name', 'code', 'code3', 'tld', 'phone']

admin.site.register(Country, CountryAdmin)

class RegionAdmin(CitiesAdmin):
    ordering = ['name_std']
    list_display = ['name_std', 'code', 'country']
    search_fields = ['name', 'name_std', 'code']

admin.site.register(Region, RegionAdmin)

class SubregionAdmin(CitiesAdmin):
    ordering = ['name_std']
    list_display = ['name_std', 'code', 'region']
    search_fields = ['name', 'name_std', 'code']
    raw_id_fields = ['alt_names', 'region']

admin.site.register(Subregion, SubregionAdmin)

class CityAdmin(CitiesAdmin):
    ordering = ['name_std']
    list_display = ['name_std', 'subregion', 'region', 'country', 'population']
    search_fields = ['name', 'name_std']
    raw_id_fields = ['alt_names', 'region', 'subregion']

admin.site.register(City, CityAdmin)

class DistrictAdmin(CitiesAdmin):
    raw_id_fields = ['alt_names', 'city']
    list_display = ['name_std', 'city']
    search_fields = ['name', 'name_std']

admin.site.register(District, DistrictAdmin)

class AltNameAdmin(admin.ModelAdmin):
    ordering = ['name']
    list_display = ['name', 'language', 'is_preferred', 'is_short']
    list_filter = ['is_preferred', 'is_short', 'language']
    search_fields = ['name']

admin.site.register(AlternativeName, AltNameAdmin)

class PostalCodeAdmin(CitiesAdmin):
    ordering = ['code']
    list_display = ['code', 'subregion_name', 'region_name', 'country']
    search_fields = ['code', 'country__name', 'region_name', 'subregion_name']

admin.site.register(PostalCode, PostalCodeAdmin)

########NEW FILE########
__FILENAME__ = conf
from importlib import import_module
from collections import defaultdict
from django.conf import settings as django_settings
    
__all__ = [
    'city_types','district_types',
    'import_opts','import_opts_all','HookException','settings'
]

url_bases = {
    'geonames': {
        'dump': 'http://download.geonames.org/export/dump/',
        'zip': 'http://download.geonames.org/export/zip/',
    },
}

files = {
    'country': {
        'filename': 'countryInfo.txt',
        'urls': [url_bases['geonames']['dump']+'{filename}', ],
        'fields': [
            'code',
            'code3',
            'codeNum',
            'fips',
            'name',
            'capital',
            'area',
            'population',
            'continent',
            'tld',
            'currencyCode',
            'currencyName',
            'phone',
            'postalCodeFormat',
            'postalCodeRegex',
            'languages',
            'geonameid',
            'neighbours',
            'equivalentFips'
        ]
    },
    'region':       {
        'filename': 'admin1CodesASCII.txt',
        'urls':     [url_bases['geonames']['dump']+'{filename}', ],
        'fields': [
            'code',
            'name',
            'asciiName',
            'geonameid',
        ]
    },
    'subregion':    {
        'filename': 'admin2Codes.txt',
        'urls':     [url_bases['geonames']['dump']+'{filename}', ],
        'fields': [
            'code',
            'name',
            'asciiName',
            'geonameid',
        ]
    },
    'city':         {
        'filename': 'cities5000.zip',
        'urls':     [url_bases['geonames']['dump']+'{filename}', ],
        'fields': [
            'geonameid',
            'name',
            'asciiName',
            'alternateNames',
            'latitude',
            'longitude',
            'featureClass',
            'featureCode',
            'countryCode',
            'cc2',
            'admin1Code',
            'admin2Code',
            'admin3Code',
            'admin4Code',
            'population',
            'elevation',
            'gtopo30',
            'timezone',
            'modificationDate'
        ]
    },
    'hierarchy':    {
        'filename': 'hierarchy.zip',
        'urls':     [url_bases['geonames']['dump']+'{filename}', ],
        'fields': [
            'parent',
            'child'
        ]
    },
    'alt_name':     {
        'filename': 'alternateNames.zip',
        'urls':     [url_bases['geonames']['dump']+'{filename}', ],
        'fields': [
            'nameid',
            'geonameid',
            'language',
            'name',
            'isPreferred',
            'isShort',
            'isColloquial',
            'isHistoric',
        ]
    },
    'postal_code':  {
        'filename': 'allCountries.zip',
        'urls':     [url_bases['geonames']['zip']+'{filename}', ],
        'fields': [
            'countryCode',
            'postalCode',
            'placeName',
            'admin1Name',
            'admin1Code',
            'admin2Name',
            'admin2Code',
            'admin3Name',
            'admin3Code',
            'latitude',
            'longitude',
            'accuracy',
        ]
    }
}

country_codes = [
    'AD','AE','AF','AG','AI','AL','AM','AO','AQ','AR','AS','AT','AU','AW','AX','AZ',
    'BA','BB','BD','BE','BF','BG','BH','BI','BJ','BL','BM','BN','BO','BQ','BR','BS','BT','BV','BW','BY','BZ',
    'CA','CC','CD','CF','CG','CH','CI','CK','CL','CM','CN','CO','CR','CU','CV','CW','CX','CY','CZ',
    'DE','DJ','DK','DM','DO','DZ','EC','EE','EG','EH','ER','ES','ET','FI','FJ','FK','FM','FO','FR',
    'GA','GB','GD','GE','GF','GG','GH','GI','GL','GM','GN','GP','GQ','GR','GS','GT','GU','GW','GY',
    'HK','HM','HN','HR','HT','HU','ID','IE','IL','IM','IN','IO','IQ','IR','IS','IT','JE','JM','JO','JP',
    'KE','KG','KH','KI','KM','KN','KP','KR','XK','KW','KY','KZ','LA','LB','LC','LI','LK','LR','LS','LT','LU','LV','LY',
    'MA','MC','MD','ME','MF','MG','MH','MK','ML','MM','MN','MO','MP','MQ','MR','MS','MT','MU','MV','MW','MX','MY','MZ',
    'NA','NC','NE','NF','NG','NI','NL','NO','NP','NR','NU','NZ','OM',
    'PA','PE','PF','PG','PH','PK','PL','PM','PN','PR','PS','PT','PW','PY','QA','RE','RO','RS','RU','RW',
    'SA','SB','SC','SD','SS','SE','SG','SH','SI','SJ','SK','SL','SM','SN','SO','SR','ST','SV','SX','SY','SZ',
    'TC','TD','TF','TG','TH','TJ','TK','TL','TM','TN','TO','TR','TT','TV','TW','TZ','UA','UG','UM','US','UY','UZ',
    'VA','VC','VE','VG','VI','VN','VU','WF','WS','YE','YT','ZA','ZM','ZW',
]

# See http://www.geonames.org/export/codes.html
city_types = ['PPL','PPLA','PPLC','PPLA2','PPLA3','PPLA4', 'PPLG']
district_types = ['PPLX']

# Command-line import options
import_opts = [
    'all',
    'country',
    'region',
    'subregion',
    'city',
    'district',
    'alt_name',
    'postal_code',
]

import_opts_all = [
    'country',
    'region',
    'subregion',
    'city',
    'district',
    'alt_name',
    'postal_code',
]

# Raise inside a hook (with an error message) to skip the current line of data.
class HookException(Exception): pass

# Hook functions that a plugin class may define
plugin_hooks = [
    'country_pre',      'country_post',
    'region_pre',       'region_post',
    'subregion_pre',    'subregion_post',
    'city_pre',         'city_post',
    'district_pre',     'district_post',
    'alt_name_pre',     'alt_name_post',
    'postal_code_pre',  'postal_code_post',
]

def create_settings():
    res = type('',(),{})
    
    res.files = files.copy()
    if hasattr(django_settings, "CITIES_FILES"):
        for key in django_settings.CITIES_FILES.keys():
            res.files[key].update(django_settings.CITIES_FILES[key])

    if hasattr(django_settings, "CITIES_LOCALES"):
        locales = django_settings.CITIES_LOCALES[:]
    else:
        locales = ['en', 'und']

    try:
        locales.remove('LANGUAGES')
        locales += [e[0] for e in django_settings.LANGUAGES]
    except: pass
    res.locales = set([e.lower() for e in locales])
    
    if hasattr(django_settings, "CITIES_POSTAL_CODES"):
        res.postal_codes = set([e.upper() for e in django_settings.CITIES_POSTAL_CODES])
    else:
        res.postal_codes = set()
    
    return res

def create_plugins():
    settings.plugins = defaultdict(list)
    for plugin in django_settings.CITIES_PLUGINS:
        module_path, classname = plugin.rsplit('.',1)
        module = import_module(module_path)
        class_ = getattr(module,classname)
        obj = class_()
        [settings.plugins[hook].append(obj) for hook in plugin_hooks if hasattr(obj,hook)]
        
settings = create_settings()
if hasattr(django_settings, "CITIES_PLUGINS"):
    create_plugins()

########NEW FILE########
__FILENAME__ = cities
"""
GeoNames city data import script.
Requires the following files:

http://download.geonames.org/export/dump/
- Countries:            countryInfo.txt
- Regions:              admin1CodesASCII.txt
- Subregions:           admin2Codes.txt
- Cities:               cities5000.zip
- Districts:            hierarchy.zip
- Localization:         alternateNames.zip

http://download.geonames.org/export/zip/
- Postal Codes:         allCountries.zip
"""

import os
import sys
import urllib
import logging
import zipfile
import time
from itertools import chain
from optparse import make_option
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify
from django.db import connection
from django.contrib.gis.gdal.envelope import Envelope
from ...conf import *
from ...models import *
from ...util import geo_distance

class Command(BaseCommand):
    app_dir = os.path.normpath(os.path.dirname(os.path.realpath(__file__)) + '/../..')
    data_dir = os.path.join(app_dir, 'data')
    logger = logging.getLogger("cities")

    option_list = BaseCommand.option_list + (
        make_option('--force', action='store_true', default=False,
            help='Import even if files are up-to-date.'
        ),
        make_option('--import', metavar="DATA_TYPES", default='all',
            help =  'Selectively import data. Comma separated list of data types: '
                    + str(import_opts).replace("'",'')
        ),
        make_option('--flush', metavar="DATA_TYPES", default='',
            help =  "Selectively flush data. Comma separated list of data types."
        ),
    )

    def handle(self, *args, **options):
        self.download_cache = {}
        self.options = options

        self.force = self.options['force']

        self.flushes = [e for e in self.options['flush'].split(',') if e]
        if 'all' in self.flushes: self.flushes = import_opts_all
        for flush in self.flushes:
            func = getattr(self, "flush_" + flush)
            func()

        self.imports = [e for e in self.options['import'].split(',') if e]
        if 'all' in self.imports: self.imports = import_opts_all
        if self.flushes: self.imports = []
        for import_ in self.imports:
            func = getattr(self, "import_" + import_)
            func()

    def call_hook(self, hook, *args, **kwargs):
        if hasattr(settings, 'plugins'):
            for plugin in settings.plugins[hook]:
                try:
                    func = getattr(plugin,hook)
                    func(self, *args, **kwargs)
                except HookException as e:
                    error = str(e)
                    if error: self.logger.error(error)
                    return False
        return True

    def download(self, filekey):
        filename = settings.files[filekey]['filename']
        web_file = None
        urls = [e.format(filename=filename) for e in settings.files[filekey]['urls']]
        for url in urls:
            try:
                web_file = urllib.urlopen(url)
                if 'html' in web_file.headers['content-type']: raise Exception()
                break
            except:
                web_file = None
                continue
        else:
            self.logger.error("Web file not found: {0}. Tried URLs:\n{1}".format(filename, '\n'.join(urls)))
            
        uptodate = False
        filepath = os.path.join(self.data_dir, filename)
        if web_file is not None:
            web_file_time = time.strptime(web_file.headers['last-modified'], '%a, %d %b %Y %H:%M:%S %Z')
            web_file_size = int(web_file.headers['content-length'])
            if os.path.exists(filepath):
                file_time = time.gmtime(os.path.getmtime(filepath))
                file_size = os.path.getsize(filepath)
                if file_time >= web_file_time and file_size == web_file_size:
                    self.logger.info("File up-to-date: " + filename)
                    uptodate = True
        else:
            self.logger.warning("Assuming file is up-to-date")
            uptodate = True
            
        if not uptodate and web_file is not None:
            self.logger.info("Downloading: " + filename)
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
            file = open(os.path.join(self.data_dir, filename), 'wb')
            file.write(web_file.read())
            file.close()
        elif not os.path.exists(filepath):
            raise Exception("File not found and download failed: " + filename)
            
        return uptodate
    
    def download_once(self, filekey):
        if filekey in self.download_cache: return self.download_cache[filekey]
        uptodate = self.download_cache[filekey] = self.download(filekey)
        return uptodate

    def get_data(self, filekey):
        filename = settings.files[filekey]['filename']
        file = open(os.path.join(self.data_dir, filename), 'rb')
        name, ext = filename.rsplit('.', 1)
        if (ext == 'zip'):
            file = zipfile.ZipFile(file).open(name + '.txt')

        data = (
            dict(zip(settings.files[filekey]['fields'], row.split("\t"))) 
            for row in file if not row.startswith('#')
        )

        return data

    def parse(self, data):
        for line in data:
            if len(line) < 1 or line[0] == '#': continue
            items = [e.strip() for e in line.split('\t')]
            yield items

    def import_country(self):
        uptodate = self.download('country')
        if uptodate and not self.force: return

        data = self.get_data('country')

        neighbours = {}
        countries = {}

        self.logger.info("Importing country data")
        for item in data:
            self.logger.info(item)
            if not self.call_hook('country_pre', item): continue
            
            country = Country()
            try: country.id = int(item['geonameid'])
            except: 
                continue

            country.name = item['name']
            country.slug = slugify(country.name)
            country.code = item['code']
            country.code3 = item['code3']
            country.population = item['population']
            country.continent = item['continent']
            country.tld = item['tld'][1:] # strip the leading .
            country.phone = item['phone']
            country.currency = item['currencyCode']
            country.currency_name = item['currencyName']
            country.capital = item['capital']
            country.area = int(float(item['area'])) if item['area'] else None
            country.languages = item['languages']

            neighbours[country] = item['neighbours'].split(",")
            countries[country.code] = country
            
            if not self.call_hook('country_post', country, item): continue 
            country.save()

        for country, neighbour_codes in neighbours.items():
            neighbours = [x for x in [countries.get(x) for x in neighbour_codes if x] if x]
            country.neighbours.add(*neighbours)
        
    def build_country_index(self):
        if hasattr(self, 'country_index'): return
        
        self.logger.info("Building country index")
        self.country_index = {}
        for obj in Country.objects.all():
            self.country_index[obj.code] = obj
            
    def import_region(self):
        uptodate = self.download('region')
        if uptodate and not self.force: return
        data = self.get_data('region')
        self.build_country_index()
                
        self.logger.info("Importing region data")
        for item in data:
            if not self.call_hook('region_pre', item): continue
            
            region = Region()

            region.id = int(item['geonameid'])
            region.name = item['name']
            region.name_std = item['asciiName']
            region.slug = slugify(region.name_std)

            country_code, region_code = item['code'].split(".")
            region.code = region_code
            try: 
                region.country = self.country_index[country_code]
            except:
                self.logger.warning("{0}: {1}: Cannot find country: {2} -- skipping".format(class_.__name__, region.name, country_code))
                continue
            
            if not self.call_hook('region_post', region, item): continue
            region.save()
            self.logger.debug("Added region: {0}, {1}".format(item['code'], region))
        
    def build_region_index(self):
        if hasattr(self, 'region_index'): return
        
        self.logger.info("Building region index")
        self.region_index = {}
        for obj in chain(Region.objects.all(), Subregion.objects.all()):
            self.region_index[obj.full_code()] = obj
            
    def import_subregion(self):
        uptodate = self.download('subregion')
        if uptodate and not self.force: return

        data = self.get_data('subregion')
        
        self.build_country_index()
        self.build_region_index()
                
        self.logger.info("Importing subregion data")
        for item in data:
            if not self.call_hook('subregion_pre', item): continue
            
            subregion = Subregion()

            subregion.id = int(item['geonameid'])
            subregion.name = item['name']
            subregion.name_std = item['asciiName']
            subregion.slug = slugify(subregion.name_std)

            country_code, region_code, subregion_code = item['code'].split(".")
            subregion.code = subregion_code
            try: 
                subregion.region = self.region_index[country_code + "." + region_code]
            except:
                self.logger.warning("Subregion: {0}: Cannot find region: {1}".format(subregion.name, region_code))
                continue
                
            if not self.call_hook('subregion_post', subregion, item): continue
            subregion.save()
            self.logger.debug("Added subregion: {0}, {1}".format(item['code'], subregion))
            
        del self.region_index
        
    def import_city(self):            
        uptodate = self.download_once('city')
        if uptodate and not self.force: return
        data = self.get_data('city')

        self.build_country_index()
        self.build_region_index()

        self.logger.info("Importing city data")
        for item in data:
            if not self.call_hook('city_pre', item): continue
            
            if item['featureCode'] not in city_types: continue

            city = City()
            try:
                city.id = int(item['geonameid'])
            except:
                continue
            city.name = item['name']
            city.kind = item['featureCode']
            city.name_std = item['asciiName']
            city.slug = slugify(city.name_std)
            city.location = Point(float(item['longitude']), float(item['latitude']))
            city.population = int(item['population'])
            city.timezone = item['timezone']
            try:
                city.elevation = int(item['elevation'])
            except:
                pass

            country_code = item['countryCode']
            try: 
                country = self.country_index[country_code]
                city.country = country
            except:
                self.logger.warning("{0}: {1}: Cannot find country: {2} -- skipping".format("CITY", city.name, country_code))
                continue

            region_code = item['admin1Code']
            try: 
                region = self.region_index[country_code + "." + region_code]
                city.region = region
            except:
                self.logger.warning("{0}: {1}: Cannot find region: {2} -- skipping".format(country_code, city.name, region_code))
                continue
            
            subregion_code = item['admin2Code']
            try: 
                subregion = self.region_index[country_code + "." + region_code + "." + subregion_code]
                city.subregion = subregion
            except:
                if subregion_code:
                    self.logger.warning("{0}: {1}: Cannot find subregion: {2} -- skipping".format(country_code, city.name, subregion_code))
                pass
            
            if not self.call_hook('city_post', city, item): continue
            city.save()
            self.logger.debug("Added city: {0}".format(city))
        
    def build_hierarchy(self):
        if hasattr(self, 'hierarchy'): return
        
        self.download('hierarchy')
        data = self.get_data('hierarchy')
        
        self.logger.info("Building hierarchy index")
        self.hierarchy = {}
        for item in data:
            parent_id = int(item['parent'])
            child_id = int(item['child'])
            self.hierarchy[child_id] = parent_id
            
    def import_district(self):
        uptodate = self.download_once('city')
        if uptodate and not self.force: return
        
        data = self.get_data('city')

        self.build_country_index()
        self.build_region_index()
        self.build_hierarchy()
            
        self.logger.info("Building city index")
        city_index = {}
        for obj in City.objects.all():
            city_index[obj.id] = obj
            
        self.logger.info("Importing district data")
        for item in data:
            if not self.call_hook('district_pre', item): continue
            
            type = item['featureCode']
            if type not in district_types: continue
            
            district = District()
            district.name = item['name']
            district.name_std = item['asciiName']
            district.slug = slugify(district.name_std)
            district.location = Point(float(item['longitude']), float(item['latitude']))
            district.population = int(item['population'])
            
            # Find city
            city = None
            try: 
                city = city_index[self.hierarchy[district.id]]
            except:
                self.logger.warning("District: {0}: Cannot find city in hierarchy, using nearest".format(district.name))
                city_pop_min = 100000
                # we are going to try to find closet city using native database .distance(...) query but if that fails
                # then we fall back to degree search, MYSQL has no support and Spatialite with SRID 4236. 
                try:
                    city = City.objects.filter(population__gt=city_pop_min).distance(district.location).order_by('distance')[0]
                except:
                    self.logger.warning("District: {0}: DB backend does not support native '.distance(...)' query " \
                                        "falling back to two degree search".format(district.name))
                    search_deg = 2
                    min_dist = float('inf')
                    bounds = Envelope(district.location.x-search_deg, district.location.y-search_deg,
                                      district.location.x+search_deg, district.location.y+search_deg)
                    for e in City.objects.filter(population__gt=city_pop_min).filter(location__intersects=bounds.wkt):
                        dist = geo_distance(district.location, e.location)
                        if dist < min_dist:
                            min_dist = dist
                            city = e
                    
            if not city:
                self.logger.warning("District: {0}: Cannot find city -- skipping".format(district.name))
                continue

            district.city = city
            
            if not self.call_hook('district_post', district, item): continue
            district.save()
            self.logger.debug("Added district: {0}".format(district))
        
    def import_alt_name(self):
        uptodate = self.download('alt_name')
        if uptodate and not self.force: return
        data = self.get_data('alt_name')
        
        self.logger.info("Building geo index")
        geo_index = {}
        for type_ in [Country, Region, Subregion, City, District]:
            for obj in type_.objects.all():
                geo_index[obj.id] = {
                    'type': type_,
                    'object': obj,
                }
        
        self.logger.info("Importing alternate name data")
        for item in data:
            if not self.call_hook('alt_name_pre', item): continue
            
            # Only get names for languages in use
            locale = item['language']
            if not locale: locale = 'und'
            if not locale in settings.locales and 'all' not in settings.locales: 
                self.logger.info("SKIPPING {0}".format(settings.locales))
                continue
            
            # Check if known geo id
            geo_id = int(item['geonameid'])
            try: geo_info = geo_index[geo_id]
            except: continue
            
            alt = AlternativeName()
            alt.id = int(item['nameid'])
            alt.name = item['name']
            alt.is_preferred = item['isPreferred']
            alt.is_short = item['isShort']
            alt.language = locale

            if not self.call_hook('alt_name_post', alt, item): continue
            alt.save()
            geo_info['object'].alt_names.add(alt)

            self.logger.debug("Added alt name: {0}, {1}".format(locale, alt))

    def import_postal_code(self):
        uptodate = self.download('postal_code')
        if uptodate and not self.force: return
        data = self.get_data('postal_code')

        self.build_country_index()
        self.build_region_index()

        self.logger.info("Importing postal codes")
        for item in data:
            if not self.call_hook('postal_code_pre', item): continue

            country_code = item['countryCode']
            if country_code not in settings.postal_codes and 'ALL' not in settings.postal_codes: continue

            # Find country
            code = item['postalCode']
            country = None
            try:
                country = self.country_index[country_code]
            except:
                self.logger.warning("Postal code: {0}: Cannot find country: {1} -- skipping".format(code, country_code))
                continue

            pc = PostalCode()
            pc.country = country
            pc.code = code
            pc.name = item['placeName']
            pc.region_name = item['admin1Name']
            pc.subregion_name = item['admin2Name']
            pc.district_name = item['admin3Name']

            try:
                pc.location = Point(float(item['longitude']), float(item['latitude']))
            except:
                self.logger.warning("Postal code: {0}, {1}: Invalid location ({2}, {3})".format(pc.country, pc.code, item['longitude'], item['latitude']))
                continue

            if not self.call_hook('postal_code_post', pc, item): continue
            self.logger.debug("Adding postal code: {0}, {1}".format(pc.country, pc))
            try:
                pc.save()
            except Exception, e:
                print e

    def flush_country(self):
        self.logger.info("Flushing country data")
        Country.objects.all().delete()
        
    def flush_region(self):
        self.logger.info("Flushing region data")
        Region.objects.all().delete()
        
    def flush_subregion(self):
        self.logger.info("Flushing subregion data")
        Subregion.objects.all().delete()
        
    def flush_city(self):
        self.logger.info("Flushing city data")
        City.objects.all().delete()
    
    def flush_district(self):
        self.logger.info("Flushing district data")
        District.objects.all().delete()
    
    def flush_alt_name(self):
        self.logger.info("Flushing alternate name data")
        [geo_alt_name.objects.all().delete() for locales in geo_alt_names.values() for geo_alt_name in locales.values()]
        
    def flush_postal_code(self):
        self.logger.info("Flushing postal code data")
        [postal_code.objects.all().delete() for postal_code in postal_codes.values()]

########NEW FILE########
__FILENAME__ = models
from django.utils.encoding import force_unicode
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from conf import settings

__all__ = [
        'Point', 'Country', 'Region', 'Subregion',
        'City', 'District', 'PostalCode', 'AlternativeName', 
]

class Place(models.Model):
    name = models.CharField(max_length=200, db_index=True, verbose_name="ascii name")
    slug = models.CharField(max_length=200)
    alt_names = models.ManyToManyField('AlternativeName')

    objects = models.GeoManager()

    class Meta:
        abstract = True

    @property
    def hierarchy(self):
        """Get hierarchy, root first"""
        list = self.parent.hierarchy if self.parent else []
        list.append(self)
        return list

    def get_absolute_url(self):
        return "/".join([place.slug for place in self.hierarchy])

    def __unicode__(self):
        return force_unicode(self.name)

class Country(Place):
    code = models.CharField(max_length=2, db_index=True)
    code3 = models.CharField(max_length=3, db_index=True)
    population = models.IntegerField()
    area = models.IntegerField(null=True)
    currency = models.CharField(max_length=3, null=True)
    currency_name = models.CharField(max_length=50, null=True)
    languages = models.CharField(max_length=250, null=True)
    phone = models.CharField(max_length=20)
    continent = models.CharField(max_length=2)
    tld = models.CharField(max_length=5)
    capital = models.CharField(max_length=100)
    neighbours = models.ManyToManyField("self")

    class Meta:
        ordering = ['name']
        verbose_name_plural = "countries"

    @property
    def parent(self):
        return None

    def __unicode__(self):
        return force_unicode(self.name)

class Region(Place):
    name_std = models.CharField(max_length=200, db_index=True, verbose_name="standard name")
    code = models.CharField(max_length=200, db_index=True)
    country = models.ForeignKey(Country)

    @property
    def parent(self):
        return self.country

    def full_code(self):
        return ".".join([self.parent.code, self.code])

class Subregion(Place):
    name_std = models.CharField(max_length=200, db_index=True, verbose_name="standard name")
    code = models.CharField(max_length=200, db_index=True)
    region = models.ForeignKey(Region)

    @property
    def parent(self):
        return self.region

    def full_code(self):
        return ".".join([self.parent.parent.code, self.parent.code, self.code])

class City(Place):
    name_std = models.CharField(max_length=200, db_index=True, verbose_name="standard name")
    location = models.PointField()
    population = models.IntegerField()
    region = models.ForeignKey(Region, null=True, blank=True)
    subregion = models.ForeignKey(Subregion, null=True, blank=True)
    country = models.ForeignKey(Country)
    elevation = models.IntegerField(null=True)
    kind = models.CharField(max_length=10) # http://www.geonames.org/export/codes.html
    timezone = models.CharField(max_length=40) 

    class Meta:
        verbose_name_plural = "cities"

    @property
    def parent(self):
        return self.region

class District(Place):
    name_std = models.CharField(max_length=200, db_index=True, verbose_name="standard name")
    location = models.PointField()
    population = models.IntegerField()
    city = models.ForeignKey(City)

    @property
    def parent(self):
        return self.city

class AlternativeName(models.Model):
    name = models.CharField(max_length=256)
    language = models.CharField(max_length=100)
    is_preferred = models.BooleanField(default=False)
    is_short = models.BooleanField(default=False)
    is_colloquial = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s (%s)" % (force_unicode(self.name), force_unicode(self.language))

class PostalCode(Place):
    code = models.CharField(max_length=20)
    location = models.PointField()

    country = models.ForeignKey(Country, related_name = 'postal_codes')

    # Region names for each admin level, region may not exist in DB
    region_name = models.CharField(max_length=100, db_index=True)
    subregion_name = models.CharField(max_length=100, db_index=True)
    district_name = models.CharField(max_length=100, db_index=True)

    objects = models.GeoManager()

    @property
    def parent(self):
        return self.country

    @property
    def name_full(self):
        """Get full name including hierarchy"""
        return u', '.join(reversed(self.names)) 

    @property
    def names(self):
        """Get a hierarchy of non-null names, root first"""
        return [e for e in [
            force_unicode(self.country),
            force_unicode(self.region_name),
            force_unicode(self.subregion_name),
            force_unicode(self.district_name),
            force_unicode(self.name),
        ] if e]

    def __unicode__(self):
        return force_unicode(self.code)

########NEW FILE########
__FILENAME__ = postal_code_ca
from ..conf import *

code_map = {
    'AB': '01',
    'BC': '02',
    'MB': '03',
    'NB': '04',
    'NL': '05',
    'NS': '07',
    'ON': '08',
    'PE': '09',
    'QC': '10',
    'SK': '11',
    'YT': '12',
    'NT': '13',
    'NU': '14',
}

class Plugin:
    def postal_code_pre(self, parser, item):
        country_code = item['countryCode']
        if country_code != 'CA': return
        item['admin1Code'] = code_map[item['admin1Code']]
        

########NEW FILE########
__FILENAME__ = util
import re
from math import radians, sin, cos, acos
from django.contrib.gis.geos import Point
    
earth_radius_km = 6371.009

def geo_distance(a, b):
    """Distance between two geo points in km. (p.x = long, p.y = lat)"""
    a_y = radians(a.y)
    b_y = radians(b.y)
    delta_x = radians(a.x - b.x)
    cos_x = (   sin(a_y) * sin(b_y) +
                cos(a_y) * cos(b_y) * cos(delta_x))
    return acos(cos_x) * earth_radius_km

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
sys.path.append('..')
from django.core.management import execute_manager
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
import os
def rel(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'HOST': 'localhost',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'OPTIONS': {
            'autocommit': True,
        }
    }
}

TEMPLATE_DIRS = (rel("templates"))
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

SECRET_KEY = 'YOUR_SECRET_KEY'

ROOT_URLCONF = 'urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.admin',
    'cities',
)

CITIES_POSTAL_CODES = ['ALL']
CITIES_LOCALES = ['ALL']

CITIES_PLUGINS = [
    'cities.plugin.postal_code_ca.Plugin',  # Canada postal codes need region codes remapped to match geonames
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'log_to_stdout': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            },
        },
    'loggers': {
        'cities': {
            'handlers': ['log_to_stdout'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf.urls import patterns
from django.contrib import admin
from django.views.generic import ListView
from cities.models import Country, Region, City, District, PostalCode

class PlaceListView(ListView):
    template_name = "list.html"

    def get_queryset(self):
        if not self.args or not self.args[0]:
            self.place = None
            return Country.objects.all()
        args = self.args[0].split("/")

        country = Country.objects.get(slug=args[0])
        if len(args) == 1:
            self.place = country
            return Region.objects.filter(country=country).order_by('name')

        region = Region.objects.get(country = country, slug=args[1])
        if len(args) == 2:
            self.place = region
            return City.objects.filter(region=region).order_by('name')

        city = City.objects.get(region = region, slug=args[2])
        self.place = city
        return District.objects.filter(city=city).order_by('name')

    def get_context_data(self, **kwargs):
        context = super(PlaceListView, self).get_context_data(**kwargs)
        context['place'] = self.place

        if hasattr(self.place, 'location'):
            context['nearby'] = City.objects.distance(self.place.location).exclude(id=self.place.id).order_by('distance')[:10]
            context['postal'] = PostalCode.objects.distance(self.place.location).order_by('distance')[:10]
        return context

admin.autodiscover()
urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^(.*)$', PlaceListView.as_view()),
)

########NEW FILE########
