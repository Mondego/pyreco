__FILENAME__ = base
# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.functional import SimpleLazyObject
from django_geoip.models import IpRange
from django_geoip.utils import get_class


location_model = SimpleLazyObject(
    lambda: get_class(settings.GEOIP_LOCATION_MODEL))


storage_class = get_class(settings.GEOIP_STORAGE_CLASS)


class Locator(object):
    """ A helper class that automates user location detection.
    """

    def __init__(self, request):
        self.request = request

    def locate(self):
        """ Find out what is user location (either from his IP or cookie).

        :return: :ref:`Custom location model <location_model>`
        """
        stored_location = self._get_stored_location()
        if not stored_location:
            ip_range = self._get_ip_range()
            stored_location = self._get_corresponding_location(ip_range)
        return stored_location

    def is_store_empty(self):
        """
        Check whether user location will be detected by ip or fetched from storage.

        Useful for integration with :ref:`django-hosts <djangohosts>`.
        """
        return self._get_stored_location() is None

    def _get_corresponding_location(self, ip_range):
        """
        Get user location by IP range, if no location matches, returns default location.

        :param ip_range: An instance of IpRange model
        :type ip_range: IpRange
        :return: Custom location model
        """
        try:
            return location_model.get_by_ip_range(ip_range)
        except ObjectDoesNotExist:
            return location_model.get_default_location()

    def _get_real_ip(self):
        """
        Get IP from request.

        :param request: A usual request object
        :type request: HttpRequest
        :return: ipv4 string or None
        """
        try:
            # Trying to work with most common proxy headers
            real_ip = self.request.META['HTTP_X_FORWARDED_FOR']
            return real_ip.split(',')[0]
        except KeyError:
            return self.request.META['REMOTE_ADDR']
        except Exception:
            # Unknown IP
            return None

    def _get_ip_range(self):
        """
        Fetches IpRange instance if request IP is found in database.

        :param request: A ususal request object
        :type request: HttpRequest
        :return: IpRange object or None
        """
        ip = self._get_real_ip()
        try:
            geobase_entry = IpRange.objects.by_ip(ip)
        except IpRange.DoesNotExist:
            geobase_entry = None
        return geobase_entry

    def _get_stored_location(self):
        """ Get location from cookie.

        :param request: A ususal request object
        :type request: HttpRequest
        :return: Custom location model
        """
        location_storage = storage_class(request=self.request, response=None)
        return location_storage.get()


########NEW FILE########
__FILENAME__ = compat
# coding: utf-8
import sys

PY3 = sys.version_info[0] == 3

if PY3:
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    import StringIO
    StringIO = BytesIO = StringIO.StringIO


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator
########NEW FILE########
__FILENAME__ = geoip_update
# -*- coding: utf-8 -*-
import logging
from optparse import make_option

from django.core.management.base import BaseCommand
from ..ipgeobase import IpGeobase


class Command(BaseCommand):

    help = 'Updates django-geoip data stored in db'
    option_list = BaseCommand.option_list + (
        make_option('--clear',
            action='store_true',
            default=False,
            help="Clear tables prior import"
        ),
    )

    def get_logger(self, verbosity):
        logger = logging.getLogger('import')
        logger.addHandler(logging.StreamHandler())
        VERBOSITY_MAPPING = {
            0: logging.CRITICAL, # no
            1: logging.INFO, # means normal output (default)
            2: logging.DEBUG, # means verbose output
            3: logging.DEBUG, # means very verbose output
        }
        logger.setLevel(VERBOSITY_MAPPING[int(verbosity)])
        return logger

    def handle(self, *args, **options):
        logger = self.get_logger(options['verbosity'])
        backend = IpGeobase(logger=logger)

        if options.get('clear'):
            backend.clear_database()

        backend.download_files()
        backend.sync_database()
########NEW FILE########
__FILENAME__ = ipgeobase
# -*- coding: utf-8 -*-
import io
import tempfile
import logging
import zipfile
from decimal import Decimal

import requests
from django.conf import settings

from django_geoip.vendor.progressbar import ProgressBar, Percentage, Bar
from django_geoip import compat
from django_geoip.models import IpRange, City, Region, Country
from .iso3166_1 import ISO_CODES


class IpGeobase(object):
    """Backend to download and update geography and ip addresses mapping.
    """

    def __init__(self, logger=None):
        self.files = {}
        self.logger = logger or logging.getLogger(name='geoip_update')

    def clear_database(self):
        """ Removes all geodata stored in database.
            Useful for development, never use on production.
        """
        self.logger.info('Removing obsolete geoip from database...')
        IpRange.objects.all().delete()
        City.objects.all().delete()
        Region.objects.all().delete()
        Country.objects.all().delete()

    def download_files(self):
        self.files = self._download_extract_archive(settings.IPGEOBASE_SOURCE_URL)
        return self.files

    def sync_database(self):
        cidr_info = self._process_cidr_file(io.open(self.files['cidr'], encoding=settings.IPGEOBASE_FILE_ENCODING))
        city_info = self._process_cities_file(io.open(self.files['cities'], encoding=settings.IPGEOBASE_FILE_ENCODING),
                                              cidr_info['city_country_mapping'])
        self.logger.info('Updating locations...')
        self._update_geography(cidr_info['countries'],
                               city_info['regions'],
                               city_info['cities'])
        self.logger.info('Updating CIDR...')
        self._update_cidr(cidr_info)

    def _download_extract_archive(self, url):
        """ Returns dict with 2 extracted filenames """
        self.logger.info('Downloading zipfile from ipgeobase.ru...')
        temp_dir = tempfile.mkdtemp()
        archive = zipfile.ZipFile(self._download_url_to_string(url))
        self.logger.info('Extracting files...')
        file_cities = archive.extract(settings.IPGEOBASE_CITIES_FILENAME, path=temp_dir)
        file_cidr = archive.extract(settings.IPGEOBASE_CIDR_FILENAME, path=temp_dir)
        return {'cities': file_cities, 'cidr': file_cidr}

    def _download_url_to_string(self, url):
        r = requests.get(url)
        return compat.BytesIO(r.content)

    def _line_to_dict(self, file, field_names):
        """ Converts file line into dictonary """
        for line in file:
            delimiter = settings.IPGEOBASE_FILE_FIELDS_DELIMITER
            yield self._extract_data_from_line(line, field_names, delimiter)

    def _extract_data_from_line(self, line, field_names=None, delimiter="\t"):
        return dict(zip(field_names, line.rstrip('\n').split(delimiter)))

    def _process_cidr_file(self, file):
        """ Iterate over ip info and extract useful data """
        data = {'cidr': list(), 'countries': set(), 'city_country_mapping': dict()}
        allowed_countries = settings.IPGEOBASE_ALLOWED_COUNTRIES
        for cidr_info in self._line_to_dict(file, field_names=settings.IPGEOBASE_CIDR_FIELDS):
            if allowed_countries and cidr_info['country_code'] not in allowed_countries:
                continue
            city_id = cidr_info['city_id'] if cidr_info['city_id'] != '-' else None
            data['cidr'].append({'start_ip': cidr_info['start_ip'],
                                 'end_ip': cidr_info['end_ip'],
                                 'country_id': cidr_info['country_code'],
                                 'city_id': city_id})
            data['countries'].add(cidr_info['country_code'])
            if city_id is not None:
                data['city_country_mapping'].update({cidr_info['city_id']: cidr_info['country_code']})
        return data

    def _get_country_code_for_city(self, city_id, mapping, added_data):
        """ Get country code for city, if we don't know exactly, lets take last used country"""
        try:
            return mapping[city_id]
        except KeyError:
            return added_data[-1]['country__code']

    def _process_cities_file(self, file, city_country_mapping):
        """ Iterate over cities info and extract useful data """
        data = {'regions': list(), 'cities': list(), 'city_region_mapping': dict()}
        allowed_countries = settings.IPGEOBASE_ALLOWED_COUNTRIES
        for geo_info in self._line_to_dict(file, field_names=settings.IPGEOBASE_CITIES_FIELDS):
            country_code = self._get_country_code_for_city(geo_info['city_id'], city_country_mapping, data['regions'])
            if allowed_countries and country_code not in allowed_countries:
                continue
            new_region = {'name': geo_info['region_name'],
                          'country__code': country_code}
            if new_region not in data['regions']:
                data['regions'].append(new_region)
            data['cities'].append({'region__name': geo_info['region_name'],
                                   'name': geo_info['city_name'],
                                   'id': geo_info['city_id'],
                                   'latitude': Decimal(geo_info['latitude']),
                                   'longitude': Decimal(geo_info['longitude'])})
        return data

    def _update_geography(self, countries, regions, cities):
        """ Update database with new countries, regions and cities """
        existing = {
            'cities': list(City.objects.values_list('id', flat=True)),
            'regions': list(Region.objects.values('name', 'country__code')),
            'countries': Country.objects.values_list('code', flat=True)
        }
        for country_code in countries:
            if country_code not in existing['countries']:
                Country.objects.create(code=country_code, name=ISO_CODES.get(country_code, country_code))
        for entry in regions:
            if entry not in existing['regions']:
                Region.objects.create(name=entry['name'], country_id=entry['country__code'])
        for entry in cities:
            if int(entry['id']) not in existing['cities']:
                region = Region.objects.get(name=entry['region__name'])
                City.objects.create(id=entry['id'], name=entry['name'], region=region,
                                    latitude=entry.get('latitude'), longitude=entry.get('longitude'))

    def _update_cidr(self, cidr):
        """ Rebuild IPRegion table with fresh data (old ip ranges are removed for simplicity)"""
        new_ip_ranges = []
        is_bulk_create_supported = hasattr(IpRange.objects, 'bulk_create')
        IpRange.objects.all().delete()
        city_region_mapping = self._build_city_region_mapping()

        if self.logger.getEffectiveLevel() in [logging.INFO, logging.DEBUG]:
            pbar = ProgressBar(widgets=[Percentage(), ' ', Bar()])
        else:
            pbar = iter
        for entry in pbar(cidr['cidr']):
            # skipping for country rows
            if entry['city_id']:
                entry.update({'region_id': city_region_mapping[int(entry['city_id'])]})
            if is_bulk_create_supported:
                new_ip_ranges.append(IpRange(**entry))
            else:
                IpRange.objects.create(**entry)
        if is_bulk_create_supported:
            IpRange.objects.bulk_create(new_ip_ranges)

    def _build_city_region_mapping(self):
        cities = City.objects.values('id', 'region__id')
        city_region_mapping = {}
        for city in cities:
            if city['id']:
                city_region_mapping.update({city['id']: city['region__id']})
        return city_region_mapping

########NEW FILE########
__FILENAME__ = iso3166_1
# -*- coding: utf-8 -*-

ISO_CODES = {
    "AF": "Afghanistan",	
    "AX": "Åland",
    "AL": "Albania",
    "DZ": "Algeria",
    "AS": "American Samoa",
    "AD": "Andorra",	
    "AO": "Angola",	
    "AI": "Anguilla",
    "AQ": "Antarctica",
    "AG": "Antigua and Barbuda",
    "AR": "Argentina",
    "AM": "Armenia",
    "AW": "Aruba",
    "AU": "Australia",
    "AT": "Austria",
    "AZ": "Azerbaijan",
    "BS": "Bahamas",
    "BH": "Bahrain",
    "BD": "Bangladesh",
    "BB": "Barbados",
    "BY": "Belarus",
    "BE": "Belgium",
    "BZ": "Belize",
    "BJ": "Benin",
    "BM": "Bermuda",
    "BT": "Bhutan",
    "BO": "Bolivia",
    "BQ": "Bonaire, Sint Eustatiusand Saba",
    "BA": "Bosnia and Herzegovina",
    "BW": "Botswana",
    "BV": "Bouvet Island",
    "BR": "Brazil",
    "IO": "British Indian Ocean Territory",
    "BN": "Brunei Darussalam",
    "BG": "Bulgaria",
    "BF": "Burkina Faso",
    "BI": "Burundi",
    "KH": "Cambodia",
    "CM": "Cameroon",
    "CA": "Canada",
    "CV": "Cape Verde",
    "KY": "Cayman Islands",
    "CF": "Central African Republic",
    "TD": "Chad",
    "CL": "Chile",
    "CN": "China",
    "CX": "Christmas Island",
    "CC": "Cocos (Keeling) Islands",
    "CO": "Colombia",
    "KM": "Comoros",
    "CG": "Congo (Brazzaville)",
    "CD": "Congo (Kinshasa)",
    "CK": "Cook Islands",
    "CR": "Costa Rica",
    "CI": "Côte d'Ivoire",
    "HR": "Croatia",
    "CU": "Cuba",
    "CW": "Curaçao",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DK": "Denmark",
    "DJ": "Djibouti",
    "DM": "Dominica",
    "DO": "Dominican Republic",
    "EC": "Ecuador",
    "EG": "Egypt",
    "SV": "El Salvador",
    "GQ": "Equatorial Guinea",
    "ER": "Eritrea",
    "EE": "Estonia",
    "ET": "Ethiopia",
    "FK": "Falkland Islands",
    "FO": "Faroe Islands",
    "FJ": "Fiji",
    "FI": "Finland",
    "FR": "France",
    "GF": "French Guiana",
    "PF": "French Polynesia",
    "TF": "French Southern Lands",
    "GA": "Gabon",
    "GM": "Gambia",
    "GE": "Georgia",
    "DE": "Germany",
    "GH": "Ghana",
    "GI": "Gibraltar",
    "GR": "Greece",
    "GL": "Greenland",
    "GD": "Grenada",
    "GP": "Guadeloupe",
    "GU": "Guam",
    "GT": "Guatemala",
    "GG": "Guernsey",
    "GN": "Guinea",
    "GW": "Guinea-Bissau",
    "GY": "Guyana",
    "HT": "Haiti",
    "HM": "Heard and McDonald Islands",
    "HN": "Honduras",
    "HK": "Hong Kong",
    "HU": "Hungary",
    "IS": "Iceland",
    "IN": "India",
    "ID": "Indonesia",
    "IR": "Iran",
    "IQ": "Iraq",
    "IE": "Ireland",
    "IM": "Isle of Man",
    "IL": "Israel",
    "IT": "Italy",
    "JM": "Jamaica",
    "JP": "Japan",
    "JE": "Jersey",
    "JO": "Jordan",
    "KZ": "Kazakhstan",
    "KE": "Kenya",
    "KI": "Kiribati",
    "KP": "Korea, North",
    "KR": "Korea, South",
    "KW": "Kuwait",
    "KG": "Kyrgyzstan",
    "LA": "Laos",
    "LV": "Latvia",
    "LB": "Lebanon",
    "LS": "Lesotho",
    "LR": "Liberia",
    "LY": "Libya",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MO": "Macau",
    "MK": "Macedonia",
    "MG": "Madagascar",
    "MW": "Malawi",
    "MY": "Malaysia",
    "MV": "Maldives",
    "ML": "Mali",
    "MT": "Malta",
    "MH": "Marshall Islands",
    "MQ": "Martinique",
    "MR": "Mauritania",
    "MU": "Mauritius",
    "YT": "Mayotte",
    "MX": "Mexico",
    "FM": "Micronesia",
    "MD": "Moldova",
    "MC": "Monaco",
    "MN": "Mongolia",
    "ME": "Montenegro",
    "MS": "Montserrat",
    "MA": "Morocco",
    "MZ": "Mozambique",
    "MM": "Myanmar",
    "NA": "Namibia",
    "NR": "Nauru",
    "NP": "Nepal",
    "NL": "Netherlands",
    "NC": "New Caledonia",
    "NZ": "New Zealand",
    "NI": "Nicaragua",
    "NE": "Niger",
    "NG": "Nigeria",
    "NU": "Niue",
    "NF": "Norfolk Island",
    "MP": "Northern Mariana Islands",
    "NO": "Norway",
    "OM": "Oman",
    "PK": "Pakistan",
    "PW": "Palau",
    "PS": "Palestine",
    "PA": "Panama",
    "PG": "Papua New Guinea",
    "PY": "Paraguay",
    "PE": "Peru",
    "PH": "Philippines",
    "PN": "Pitcairn",
    "PL": "Poland",
    "PT": "Portugal",
    "PR": "Puerto Rico",
    "QA": "Qatar",
    "RE": "Reunion",
    "RO": "Romania",
    "RU": "Russian Federation",
    "RW": "Rwanda",
    "BL": "Saint Barthélemy",
    "SH": "Saint Helena",
    "KN": "Saint Kitts and Nevis",
    "LC": "Saint Lucia",
    "MF": "Saint Martin (French part)",
    "PM": "Saint Pierre and Miquelon",
    "VC": "Saint Vincent and theGrenadines",
    "WS": "Samoa",
    "SM": "San Marino",
    "ST": "Sao Tome and Principe",
    "SA": "Saudi Arabia",
    "SN": "Senegal",
    "RS": "Serbia",
    "SC": "Seychelles",
    "SL": "Sierra Leone",
    "SG": "Singapore",
    "SX": "Sint Maarten",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "SB": "Solomon Islands",
    "SO": "Somalia",
    "ZA": "South Africa",
    "GS": "South Georgia and South Sandwich Islands",
    "SS": "South Sudan",
    "ES": "Spain",
    "LK": "Sri Lanka",
    "SD": "Sudan",
    "SR": "Suriname",
    "SJ": "Svalbard and Jan Mayen Islands",
    "SZ": "Swaziland",
    "SE": "Sweden",
    "CH": "Switzerland",
    "SY": "Syria",
    "TW": "Taiwan",
    "TJ": "Tajikistan",
    "TZ": "Tanzania",
    "TH": "Thailand",
    "TL": "Timor-Leste",
    "TG": "Togo",
    "TK": "Tokelau",
    "TO": "Tonga",
    "TT": "Trinidad and Tobago",
    "TN": "Tunisia",
    "TR": "Turkey",
    "TM": "Turkmenistan",
    "TC": "Turks and Caicos Islands",
    "TV": "Tuvalu",
    "UG": "Uganda",
    "UA": "Ukraine",
    "AE": "United Arab Emirates",
    "GB": "United Kingdom",
    "UM": "United States Minor Outlying Islands",
    "US": "United States of America",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "VU": "Vanuatu",
    "VA": "Vatican City",
    "VE": "Venezuela",
    "VN": "Vietnam",
    "VG": "Virgin Islands, British",
    "VI": "Virgin Islands, U.S.",
    "WF": "Wallis and Futuna Islands",
    "EH": "Western Sahara",
    "YE": "Yemen",
    "ZM": "Zambia",
    "ZW": "Zimbabwe",
}
########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
from django.utils.functional import SimpleLazyObject
from django_geoip.base import storage_class


def get_location(request):
    from django_geoip.base import Locator
    if not hasattr(request, '_cached_location'):
        request._cached_location = Locator(request).locate()
    return request._cached_location


class LocationMiddleware(object):

    def process_request(self, request):
        """ Don't detect location, until we request it implicitly """
        request.location = SimpleLazyObject(lambda: get_location(request))

    def process_response(self, request, response):
        """ Do nothing, if process_request never completed (redirect)"""
        if not hasattr(request, 'location'):
            return response

        storage = storage_class(request=request, response=response)
        try:
            storage.set(location=request.location)
        except ValueError:
            # bad location_id
            pass
        return response

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Country'
        db.create_table('django_geoip_country', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=2, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
        ))
        db.send_create_signal('django_geoip', ['Country'])

        # Adding model 'Region'
        db.create_table('django_geoip_region', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(related_name='regions', to=orm['django_geoip.Country'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('django_geoip', ['Region'])

        # Adding unique constraint on 'Region', fields ['country', 'name']
        db.create_unique('django_geoip_region', ['country_id', 'name'])

        # Adding model 'City'
        db.create_table('django_geoip_city', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('region', self.gf('django.db.models.fields.related.ForeignKey')(related_name='cities', to=orm['django_geoip.Region'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('latitude', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=9, decimal_places=6, blank=True)),
            ('longitude', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=9, decimal_places=6, blank=True)),
        ))
        db.send_create_signal('django_geoip', ['City'])

        # Adding unique constraint on 'City', fields ['region', 'name']
        db.create_unique('django_geoip_city', ['region_id', 'name'])

        # Adding model 'IpRange'
        db.create_table('django_geoip_iprange', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start_ip', self.gf('django.db.models.fields.BigIntegerField')(db_index=True)),
            ('end_ip', self.gf('django.db.models.fields.BigIntegerField')(db_index=True)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_geoip.Country'])),
            ('region', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_geoip.Region'], null=True)),
            ('city', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_geoip.City'], null=True)),
        ))
        db.send_create_signal('django_geoip', ['IpRange'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'City', fields ['region', 'name']
        db.delete_unique('django_geoip_city', ['region_id', 'name'])

        # Removing unique constraint on 'Region', fields ['country', 'name']
        db.delete_unique('django_geoip_region', ['country_id', 'name'])

        # Deleting model 'Country'
        db.delete_table('django_geoip_country')

        # Deleting model 'Region'
        db.delete_table('django_geoip_region')

        # Deleting model 'City'
        db.delete_table('django_geoip_city')

        # Deleting model 'IpRange'
        db.delete_table('django_geoip_iprange')


    models = {
        'django_geoip.city': {
            'Meta': {'unique_together': "(('region', 'name'),)", 'object_name': 'City'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '6', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '6', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cities'", 'to': "orm['django_geoip.Region']"})
        },
        'django_geoip.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '2', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'django_geoip.iprange': {
            'Meta': {'object_name': 'IpRange'},
            'city': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_geoip.City']", 'null': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_geoip.Country']"}),
            'end_ip': ('django.db.models.fields.BigIntegerField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_geoip.Region']", 'null': 'True'}),
            'start_ip': ('django.db.models.fields.BigIntegerField', [], {'db_index': 'True'})
        },
        'django_geoip.region': {
            'Meta': {'unique_together': "(('country', 'name'),)", 'object_name': 'Region'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'regions'", 'to': "orm['django_geoip.Country']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['django_geoip']

########NEW FILE########
__FILENAME__ = 0002_countrynames
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django_geoip.management.iso3166_1 import ISO_CODES

class Migration(DataMigration):

    def forwards(self, orm):
        for country in orm.Country.objects.all():
            if country.code in ISO_CODES:
                country.name = ISO_CODES[country.code]
                country.save()


    def backwards(self, orm):
        for country in orm.Country.objects.all():
            country.name = country.code
            country.save()


    models = {
        'django_geoip.city': {
            'Meta': {'unique_together': "(('region', 'name'),)", 'object_name': 'City'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '6', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '6', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cities'", 'to': "orm['django_geoip.Region']"})
        },
        'django_geoip.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '2', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'django_geoip.iprange': {
            'Meta': {'object_name': 'IpRange'},
            'city': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_geoip.City']", 'null': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_geoip.Country']"}),
            'end_ip': ('django.db.models.fields.BigIntegerField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_geoip.Region']", 'null': 'True'}),
            'start_ip': ('django.db.models.fields.BigIntegerField', [], {'db_index': 'True'})
        },
        'django_geoip.region': {
            'Meta': {'unique_together': "(('country', 'name'),)", 'object_name': 'Region'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'regions'", 'to': "orm['django_geoip.Country']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['django_geoip']
    symmetrical = True

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import socket
import struct
from abc import ABCMeta

from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _

# keep imports
from . import compat
from .settings import geoip_settings, ipgeobase_settings


class Country(models.Model):
    """ One country per row, contains country code and country name.
    """
    code = models.CharField(_('country code'), max_length=2, primary_key=True)
    name = models.CharField(_('country name'), max_length=255, unique=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('country')
        verbose_name_plural = _('countries')


class Region(models.Model):
    """ Region is a some geographical entity that belongs to one Country,
        Cities belong to one specific Region.
        Identified by country and name.
    """
    country = models.ForeignKey(Country, related_name='regions')
    name = models.CharField(_('region name'), max_length=255)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('region')
        verbose_name_plural = _('regions')
        unique_together = (('country', 'name'), )


class City(models.Model):
    """ Geopoint that belongs to the Region and Country.
        Identified by name and region.
        Contains additional latitude/longitude info.
    """
    region = models.ForeignKey(Region, related_name='cities')
    name = models.CharField(_('city name'), max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('city')
        verbose_name_plural = _('cities')
        unique_together = (('region', 'name'), )


def inet_aton(ip):
    """ Convert string IP representation to integer
    """
    return struct.unpack('!L', socket.inet_aton(ip))[0]


class IpRangeManager(models.Manager):

    def by_ip(self, ip):
        """ Find the smallest range containing the given IP.
        """
        try:
            number = inet_aton(ip)
        except Exception:
            raise IpRange.DoesNotExist

        try:
            return super(IpRangeManager, self).get_query_set()\
                                              .filter(start_ip__lte=number, end_ip__gte=number)\
                                              .order_by('end_ip', '-start_ip')[0]
        except IndexError:
            raise IpRange.DoesNotExist


class IpRange(models.Model):
    """ IP ranges are stored in separate table, one row for each ip range.

        Each range might be associated with either country (for IP ranges outside of Russia and Ukraine)
        or country, region and city together.

        Ip range borders are `stored as long integers
        <http://publibn.boulder.ibm.com/doc_link/en_US/a_doc_lib/libs/commtrf2/inet_addr.htm>`_
    """
    start_ip = models.BigIntegerField(_('Ip range block beginning, as integer'), db_index=True)
    end_ip = models.BigIntegerField(_('Ip range block ending, as integer'), db_index=True)
    country = models.ForeignKey(Country)
    region = models.ForeignKey(Region, null=True)
    city = models.ForeignKey(City, null=True)

    objects = IpRangeManager()

    class Meta:
        verbose_name = _('IP range')
        verbose_name_plural = _("IP ranges")


class abstractclassmethod(classmethod):
    """ Abstract classmethod decorator from python 3"""
    __isabstractmethod__ = True

    def __init__(self, callable):
        callable.__isabstractmethod__ = True
        super(abstractclassmethod, self).__init__(callable)


class AbsractModel(ABCMeta, ModelBase):
    pass


class GeoLocationFacade(compat.with_metaclass(AbsractModel), models.Model):
    """ Interface for custom geographic models.
        Model represents a Facade pattern for concrete GeoIP models.
    """

    @abstractclassmethod
    def get_by_ip_range(cls, ip_range):
        """
        Return single model instance for given IP range.
        If no location matches the range, raises DoesNotExist exception.

        :param ip_range: User's IpRange to search for.
        :type ip_range: IpRange
        :return: GeoLocationFacade single object
        """
        return NotImplemented

    @abstractclassmethod
    def get_default_location(cls):
        """
        Return default location for cases where ip geolocation fails.

        :return: GeoLocationFacade
        """
        return NotImplemented

    @abstractclassmethod
    def get_available_locations(cls):
        """
        Return all locations available for users to select in frontend

        :return: GeoLocationFacade
        """
        return NotImplemented

    class Meta:
        abstract = True
########NEW FILE########
__FILENAME__ = geoip_settings
# coding: utf-8
from appconf import AppConf


class GeoIpConfig(AppConf):
    """ GeoIP configuration """

    #: A reference to a :ref:`model <location_model>` that stores custom geography, specific to application.
    LOCATION_MODEL = 'django_geoip.models.GeoLocationFacade'

    #: Persistent storage class for user location
    # (LocationCookieStorage or LocationDummyStorage are available).
    STORAGE_CLASS = 'django_geoip.storage.LocationCookieStorage'

    #: Cookie name for LocationCookieStorage class (stores :ref:`custom location's <location_model>` primary key).
    COOKIE_NAME = 'geoip_location_id'

    #: Cookie domain for LocationCookieStorage class.
    COOKIE_DOMAIN = ''

    #: Cookie lifetime in seconds (1 year by default) for LocationCookieStorage class.
    COOKIE_EXPIRES = 31622400

    #: Empty value for location, if location not found in ranges.
    #: This value must be returned in a :ref:`custom location model <location_model>`
    #: in get_default_location class method if necessary.
    LOCATION_EMPTY_VALUE = 0

    class Meta:
       prefix = 'geoip'
########NEW FILE########
__FILENAME__ = ipgeobase_settings
# coding: utf-8
from appconf import AppConf


class IpGeoBaseConfig(AppConf):
    # URL, where to download ipgeobase file from
    SOURCE_URL = 'http://ipgeobase.ru/files/db/Main/geo_files.zip'

    FILE_FIELDS_DELIMITER = "\t"
    FILE_ENCODING = 'windows-1251'

    CITIES_FILENAME = 'cities.txt'
    # 1	Хмельницкий	Хмельницкая область	Центральная Украина	49.416668	27.000000
    # <идентификатор города> <название города> <название региона> <название округа>
    # <широта центра города> <долгота центра города>
    CITIES_FIELDS = ['city_id', 'city_name', 'region_name', 'district_name', 'latitude', 'longitude']

    CIDR_FILENAME = 'cidr_optim.txt'
    #    1578795008	1578827775	94.26.128.0 - 94.26.255.255	RU	2287
    CIDR_FIELDS = ['start_ip', 'end_ip', 'ip_range_human', 'country_code', 'city_id']

    # A list of countries to use from ipgeobase.
    # By default, all countries are imported and used.
    # For example: ['RU', 'UA'] will limit database to 2 countries: Russia and Ukraine.
    ALLOWED_COUNTRIES = []

    class Meta:
       prefix = 'ipgeobase'

########NEW FILE########
__FILENAME__ = storage
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from .utils import get_class


class BaseLocationStorage(object):
    """ Base class for user location storage
    """
    def __init__(self, request, response):
        self.request = request
        self.response = response
        self.location_model = get_class(settings.GEOIP_LOCATION_MODEL)

    def get(self):
        raise NotImplemented

    def set(self, location=None, force=False):
        raise NotImplemented

    def _validate_location(self, location):
        if location == settings.GEOIP_LOCATION_EMPTY_VALUE:
            return True
        if not isinstance(location, self.location_model):
            return False
        try:
            return self.location_model.objects.filter(pk=location.id).exists()
        except AttributeError:
            raise

    def _get_by_id(self, location_id):
        return get_class(settings.GEOIP_LOCATION_MODEL).objects.get(pk=location_id)


class LocationDummyStorage(BaseLocationStorage):
    """ Fake storage for debug or when location doesn't neet to be stored
    """
    def get(self):
        return getattr(self.request, 'location', None)

    def set(self, location=None, force=False):
        pass


class LocationCookieStorage(BaseLocationStorage):
    """ Class that deals with saving user location on client's side (cookies)
    """

    def _get_location_id(self):
        return self.request.COOKIES.get(settings.GEOIP_COOKIE_NAME, None)

    def get(self):
        location_id = self._get_location_id()

        if location_id:
            try:
                return self._get_by_id(location_id)
            except (ObjectDoesNotExist, ValueError):
                pass
        return None

    def set(self, location=None, force=False):
        if not self._validate_location(location):
            raise ValueError
        empty_value = settings.GEOIP_LOCATION_EMPTY_VALUE
        cookie_value = empty_value if location == empty_value else location.id
        if force or self._should_update_cookie(cookie_value):
            self._do_set(cookie_value)

    def get_cookie_domain(self):
        if settings.GEOIP_COOKIE_DOMAIN:
            return settings.GEOIP_COOKIE_DOMAIN
        else:
            return None

    def _do_set(self, value):
        self.response.set_cookie(
            key=settings.GEOIP_COOKIE_NAME,
            value=value,
            domain=self.get_cookie_domain(),
            expires=datetime.utcnow() + timedelta(seconds=settings.GEOIP_COOKIE_EXPIRES))

    def _should_update_cookie(self, new_value):
        # process_request never completed, don't need to update cookie
        if not hasattr(self.request, 'location'):
            return False
        # Cookie doesn't exist, we need to store it
        if settings.GEOIP_COOKIE_NAME not in self.request.COOKIES:
            return True
        # Cookie is obsolete, because we've changed it's value during request
        if str(self._get_location_id()) != str(new_value):
            return True
        return False
########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
try:
    from django.conf.urls import *
except ImportError:
    from django.conf.urls.defaults import *

from django_geoip.views import set_location

urlpatterns = patterns('',
    url(r'^setlocation/', set_location, name='geoip_change_location'),
)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

def get_class(class_string):
    """
    Convert a string version of a function name to the callable object.
    """
    try:
        mod_name, class_name = get_mod_func(class_string)
        if class_name != '':
            cls = getattr(__import__(mod_name, {}, {}, ['']), class_name)
            return cls
    except (ImportError, AttributeError):
        pass
    raise ImportError('Failed to import %s' % class_string)


def get_mod_func(class_string):
    """
    Converts 'django.views.news.stories.story_detail' to
    ('django.views.news.stories', 'story_detail')

    Taken from django.core.urlresolvers
    """
    try:
        dot = class_string.rindex('.')
    except ValueError:
        return class_string, ''
    return class_string[:dot], class_string[dot + 1:]
########NEW FILE########
__FILENAME__ = compat
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# progressbar  - Text progress bar library for Python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Compatibility methods and classes for the progressbar module."""


# Python 3.x (and backports) use a modified iterator syntax
# This will allow 2.x to behave with 3.x iterators
try:
  next
except NameError:
    def next(iter):
        try:
            # Try new style iterators
            return iter.__next__()
        except AttributeError:
            # Fallback in case of a "native" iterator
            return iter.next()


# Python < 2.5 does not have "any"
try:
  any
except NameError:
   def any(iterator):
      for item in iterator:
         if item: return True
      return False

########NEW FILE########
__FILENAME__ = progressbar
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# progressbar  - Text progress bar library for Python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Main ProgressBar class."""

from __future__ import division

import math
import os
import signal
import sys
import time
from . import widgets

try:
    from fcntl import ioctl
    from array import array
    import termios
except ImportError:
    pass


class UnknownLength: pass


class ProgressBar(object):
    """The ProgressBar class which updates and prints the bar.

    A common way of using it is like:
    >>> pbar = ProgressBar().start()
    >>> for i in range(100):
    ...    # do something
    ...    pbar.update(i+1)
    ...
    >>> pbar.finish()

    You can also use a ProgressBar as an iterator:
    >>> progress = ProgressBar()
    >>> for i in progress(some_iterable):
    ...    # do something
    ...

    Since the progress bar is incredibly customizable you can specify
    different widgets of any type in any order. You can even write your own
    widgets! However, since there are already a good number of widgets you
    should probably play around with them before moving on to create your own
    widgets.

    The term_width parameter represents the current terminal width. If the
    parameter is set to an integer then the progress bar will use that,
    otherwise it will attempt to determine the terminal width falling back to
    80 columns if the width cannot be determined.

    When implementing a widget's update method you are passed a reference to
    the current progress bar. As a result, you have access to the
    ProgressBar's methods and attributes. Although there is nothing preventing
    you from changing the ProgressBar you should treat it as read only.

    Useful methods and attributes include (Public API):
     - currval: current progress (0 <= currval <= maxval)
     - maxval: maximum (and final) value
     - finished: True if the bar has finished (reached 100%)
     - start_time: the time when start() method of ProgressBar was called
     - seconds_elapsed: seconds elapsed since start_time and last call to
                        update
     - percentage(): progress in percent [0..100]
    """

    __slots__ = ('currval', 'fd', 'finished', 'last_update_time',
                 'left_justify', 'maxval', 'next_update', 'num_intervals',
                 'poll', 'seconds_elapsed', 'signal_set', 'start_time',
                 'term_width', 'update_interval', 'widgets', '_time_sensitive',
                 '__iterable')

    _DEFAULT_MAXVAL = 100
    _DEFAULT_TERMSIZE = 80
    _DEFAULT_WIDGETS = [widgets.Percentage(), ' ', widgets.Bar()]

    def __init__(self, maxval=None, widgets=None, term_width=None, poll=1,
                 left_justify=True, fd=sys.stderr):
        """Initializes a progress bar with sane defaults."""

        # Don't share a reference with any other progress bars
        if widgets is None:
            widgets = list(self._DEFAULT_WIDGETS)

        self.maxval = maxval
        self.widgets = widgets
        self.fd = fd
        self.left_justify = left_justify

        self.signal_set = False
        if term_width is not None:
            self.term_width = term_width
        else:
            try:
                self._handle_resize()
                signal.signal(signal.SIGWINCH, self._handle_resize)
                self.signal_set = True
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.term_width = self._env_size()

        self.__iterable = None
        self._update_widgets()
        self.currval = 0
        self.finished = False
        self.last_update_time = None
        self.poll = poll
        self.seconds_elapsed = 0
        self.start_time = None
        self.update_interval = 1


    def __call__(self, iterable):
        """Use a ProgressBar to iterate through an iterable."""

        try:
            self.maxval = len(iterable)
        except:
            if self.maxval is None:
                self.maxval = UnknownLength

        self.__iterable = iter(iterable)
        return self


    def __iter__(self):
        return self


    def __next__(self):
        try:
            value = next(self.__iterable)
            if self.start_time is None: self.start()
            else: self.update(self.currval + 1)
            return value
        except StopIteration:
            self.finish()
            raise


    # Create an alias so that Python 2.x won't complain about not being
    # an iterator.
    next = __next__


    def _env_size(self):
        """Tries to find the term_width from the environment."""

        return int(os.environ.get('COLUMNS', self._DEFAULT_TERMSIZE)) - 1


    def _handle_resize(self, signum=None, frame=None):
        """Tries to catch resize signals sent from the terminal."""

        h, w = array('h', ioctl(self.fd, termios.TIOCGWINSZ, '\0' * 8))[:2]
        self.term_width = w


    def percentage(self):
        """Returns the progress as a percentage."""
        return self.currval * 100.0 / self.maxval

    percent = property(percentage)


    def _format_widgets(self):
        result = []
        expanding = []
        width = self.term_width

        for index, widget in enumerate(self.widgets):
            if isinstance(widget, widgets.WidgetHFill):
                result.append(widget)
                expanding.insert(0, index)
            else:
                widget = widgets.format_updatable(widget, self)
                result.append(widget)
                width -= len(widget)

        count = len(expanding)
        while count:
            portion = max(int(math.ceil(width * 1. / count)), 0)
            index = expanding.pop()
            count -= 1

            widget = result[index].update(self, portion)
            width -= len(widget)
            result[index] = widget

        return result


    def _format_line(self):
        """Joins the widgets and justifies the line."""

        widgets = ''.join(self._format_widgets())

        if self.left_justify: return widgets.ljust(self.term_width)
        else: return widgets.rjust(self.term_width)


    def _need_update(self):
        """Returns whether the ProgressBar should redraw the line."""
        if self.currval >= self.next_update or self.finished: return True

        delta = time.time() - self.last_update_time
        return self._time_sensitive and delta > self.poll


    def _update_widgets(self):
        """Checks all widgets for the time sensitive bit."""

        self._time_sensitive = any(getattr(w, 'TIME_SENSITIVE', False)
                                    for w in self.widgets)


    def update(self, value=None):
        """Updates the ProgressBar to a new value."""

        if value is not None and value is not UnknownLength:
            if (self.maxval is not UnknownLength
                and not 0 <= value <= self.maxval):

                raise ValueError('Value out of range')

            self.currval = value


        if not self._need_update(): return
        if self.start_time is None:
            raise RuntimeError('You must call "start" before calling "update"')

        now = time.time()
        self.seconds_elapsed = now - self.start_time
        self.next_update = self.currval + self.update_interval
        self.fd.write(self._format_line() + '\r')
        self.last_update_time = now


    def start(self):
        """Starts measuring time, and prints the bar at 0%.

        It returns self so you can use it like this:
        >>> pbar = ProgressBar().start()
        >>> for i in range(100):
        ...    # do something
        ...    pbar.update(i+1)
        ...
        >>> pbar.finish()
        """

        if self.maxval is None:
            self.maxval = self._DEFAULT_MAXVAL

        self.num_intervals = max(100, self.term_width)
        self.next_update = 0

        if self.maxval is not UnknownLength:
            if self.maxval < 0: raise ValueError('Value out of range')
            self.update_interval = self.maxval / self.num_intervals


        self.start_time = self.last_update_time = time.time()
        self.update(0)

        return self


    def finish(self):
        """Puts the ProgressBar bar in the finished state."""

        self.finished = True
        self.update(self.maxval)
        self.fd.write('\n')
        if self.signal_set:
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)

########NEW FILE########
__FILENAME__ = widgets
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# progressbar  - Text progress bar library for Python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Default ProgressBar widgets."""

from __future__ import division

import datetime
import math

try:
    from abc import ABCMeta, abstractmethod
except ImportError:
    AbstractWidget = object
    abstractmethod = lambda fn: fn
else:
    AbstractWidget = ABCMeta('AbstractWidget', (object,), {})


def format_updatable(updatable, pbar):
    if hasattr(updatable, 'update'): return updatable.update(pbar)
    else: return updatable


class Widget(AbstractWidget):
    """The base class for all widgets.

    The ProgressBar will call the widget's update value when the widget should
    be updated. The widget's size may change between calls, but the widget may
    display incorrectly if the size changes drastically and repeatedly.

    The boolean TIME_SENSITIVE informs the ProgressBar that it should be
    updated more often because it is time sensitive.
    """

    TIME_SENSITIVE = False
    __slots__ = ()

    @abstractmethod
    def update(self, pbar):
        """Updates the widget.

        pbar - a reference to the calling ProgressBar
        """


class WidgetHFill(Widget):
    """The base class for all variable width widgets.

    This widget is much like the \\hfill command in TeX, it will expand to
    fill the line. You can use more than one in the same line, and they will
    all have the same width, and together will fill the line.
    """

    @abstractmethod
    def update(self, pbar, width):
        """Updates the widget providing the total width the widget must fill.

        pbar - a reference to the calling ProgressBar
        width - The total width the widget must fill
        """


class Timer(Widget):
    """Widget which displays the elapsed seconds."""

    __slots__ = ('format_string',)
    TIME_SENSITIVE = True

    def __init__(self, format='Elapsed Time: %s'):
        self.format_string = format

    @staticmethod
    def format_time(seconds):
        """Formats time as the string "HH:MM:SS"."""

        return str(datetime.timedelta(seconds=int(seconds)))


    def update(self, pbar):
        """Updates the widget to show the elapsed time."""

        return self.format_string % self.format_time(pbar.seconds_elapsed)


class ETA(Timer):
    """Widget which attempts to estimate the time of arrival."""

    TIME_SENSITIVE = True

    def update(self, pbar):
        """Updates the widget to show the ETA or total time when finished."""

        if pbar.currval == 0:
            return 'ETA:  --:--:--'
        elif pbar.finished:
            return 'Time: %s' % self.format_time(pbar.seconds_elapsed)
        else:
            elapsed = pbar.seconds_elapsed
            eta = elapsed * pbar.maxval / pbar.currval - elapsed
            return 'ETA:  %s' % self.format_time(eta)


class FileTransferSpeed(Widget):
    """Widget for showing the transfer speed (useful for file transfers)."""

    FORMAT = '%6.2f %s%s/s'
    PREFIXES = ' kMGTPEZY'
    __slots__ = ('unit',)

    def __init__(self, unit='B'):
        self.unit = unit

    def update(self, pbar):
        """Updates the widget with the current SI prefixed speed."""

        if pbar.seconds_elapsed < 2e-6 or pbar.currval < 2e-6: # =~ 0
            scaled = power = 0
        else:
            speed = pbar.currval / pbar.seconds_elapsed
            power = int(math.log(speed, 1000))
            scaled = speed / 1000.**power

        return self.FORMAT % (scaled, self.PREFIXES[power], self.unit)


class AnimatedMarker(Widget):
    """An animated marker for the progress bar which defaults to appear as if
    it were rotating.
    """

    __slots__ = ('markers', 'curmark')

    def __init__(self, markers='|/-\\'):
        self.markers = markers
        self.curmark = -1

    def update(self, pbar):
        """Updates the widget to show the next marker or the first marker when
        finished"""

        if pbar.finished: return self.markers[0]

        self.curmark = (self.curmark + 1) % len(self.markers)
        return self.markers[self.curmark]

# Alias for backwards compatibility
RotatingMarker = AnimatedMarker


class Counter(Widget):
    """Displays the current count."""

    __slots__ = ('format_string',)

    def __init__(self, format='%d'):
        self.format_string = format

    def update(self, pbar):
        return self.format_string % pbar.currval


class Percentage(Widget):
    """Displays the current percentage as a number with a percent sign."""

    def update(self, pbar):
        return '%3d%%' % pbar.percentage()


class FormatLabel(Timer):
    """Displays a formatted label."""

    mapping = {
        'elapsed': ('seconds_elapsed', Timer.format_time),
        'finished': ('finished', None),
        'last_update': ('last_update_time', None),
        'max': ('maxval', None),
        'seconds': ('seconds_elapsed', None),
        'start': ('start_time', None),
        'value': ('currval', None)
    }

    __slots__ = ('format_string',)
    def __init__(self, format):
        self.format_string = format

    def update(self, pbar):
        context = {}
        for name, (key, transform) in self.mapping.items():
            try:
                value = getattr(pbar, key)

                if transform is None:
                   context[name] = value
                else:
                   context[name] = transform(value)
            except: pass

        return self.format_string % context


class SimpleProgress(Widget):
    """Returns progress as a count of the total (e.g.: "5 of 47")."""

    __slots__ = ('sep',)

    def __init__(self, sep=' of '):
        self.sep = sep

    def update(self, pbar):
        return '%d%s%d' % (pbar.currval, self.sep, pbar.maxval)


class Bar(WidgetHFill):
    """A progress bar which stretches to fill the line."""

    __slots__ = ('marker', 'left', 'right', 'fill', 'fill_left')

    def __init__(self, marker='#', left='|', right='|', fill=' ',
                 fill_left=True):
        """Creates a customizable progress bar.

        marker - string or updatable object to use as a marker
        left - string or updatable object to use as a left border
        right - string or updatable object to use as a right border
        fill - character to use for the empty part of the progress bar
        fill_left - whether to fill from the left or the right
        """
        self.marker = marker
        self.left = left
        self.right = right
        self.fill = fill
        self.fill_left = fill_left


    def update(self, pbar, width):
        """Updates the progress bar and its subcomponents."""

        left, marked, right = (format_updatable(i, pbar) for i in
                               (self.left, self.marker, self.right))

        width -= len(left) + len(right)
        # Marked must *always* have length of 1
        if pbar.maxval:
          marked *= int(pbar.currval / pbar.maxval * width)
        else:
          marked = ''

        if self.fill_left:
            return '%s%s%s' % (left, marked.ljust(width, self.fill), right)
        else:
            return '%s%s%s' % (left, marked.rjust(width, self.fill), right)


class ReverseBar(Bar):
    """A bar which has a marker which bounces from side to side."""

    def __init__(self, marker='#', left='|', right='|', fill=' ',
                 fill_left=False):
        """Creates a customizable progress bar.

        marker - string or updatable object to use as a marker
        left - string or updatable object to use as a left border
        right - string or updatable object to use as a right border
        fill - character to use for the empty part of the progress bar
        fill_left - whether to fill from the left or the right
        """
        self.marker = marker
        self.left = left
        self.right = right
        self.fill = fill
        self.fill_left = fill_left


class BouncingBar(Bar):
    def update(self, pbar, width):
        """Updates the progress bar and its subcomponents."""

        left, marker, right = (format_updatable(i, pbar) for i in
                               (self.left, self.marker, self.right))

        width -= len(left) + len(right)

        if pbar.finished: return '%s%s%s' % (left, width * marker, right)

        position = int(pbar.currval % (width * 2 - 1))
        if position > width: position = width * 2 - position
        lpad = self.fill * (position - 1)
        rpad = self.fill * (width - len(marker) - len(lpad))

        # Swap if we want to bounce the other way
        if not self.fill_left: rpad, lpad = lpad, rpad

        return '%s%s%s%s%s' % (left, lpad, marker, rpad, right)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django import http
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django_geoip.base import storage_class
from django_geoip.utils import get_class

def set_location(request):
    """
    Redirect to a given url while setting the chosen location in the
    cookie. The url and the location_id need to be
    specified in the request parameters.

    Since this view changes how the user will see the rest of the site, it must
    only be accessed as a POST request. If called as a GET request, it will
    redirect to the page in the request (the 'next' parameter) without changing
    any state.
    """
    next = request.REQUEST.get('next', None)
    if not next:
        next = request.META.get('HTTP_REFERER', None)
    if not next:
        next = '/'
    response = http.HttpResponseRedirect(next)
    if request.method == 'POST':
        location_id = request.POST.get('location_id', None) or request.POST.get('location', None)
        if location_id:
            try:
                location = get_class(settings.GEOIP_LOCATION_MODEL).objects.get(pk=location_id)
                storage_class(request=request, response=response).set(location=location, force=True)
            except (ValueError, ObjectDoesNotExist):
                pass
    return response
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-geoip documentation build configuration file, created by
# sphinx-quickstart on Wed Jan 18 14:55:29 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'test_app.test_settings'

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-geoip'
copyright = u'2012, coagulant'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3.1'
# The full version, including alpha/beta/rc tags.
release = '0.3.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-geoipdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-geoip.tex', u'django-geoip Documentation',
   u'coagulant', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-geoip', u'django-geoip Documentation',
     [u'coagulant'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-geoip', u'django-geoip Documentation',
   u'coagulant', 'django-geoip', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_app.test_settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
########NEW FILE########
__FILENAME__ = factory
import random
import string
from django_geoip.models import Region, City, Country, IpRange


def _random_str():
    return ''.join(random.choice(string.ascii_letters) for x in range(10))


def any_country(**kwargs):
    name = kwargs.get('name', _random_str())
    code = kwargs.get('code', _random_str())
    return Country.objects.create(name=name, code=code)


def any_region(**kwargs):
    country = kwargs.get('country', any_country())
    return Region.objects.create(name=_random_str(), country=country)


def any_city(**kwargs):
    region = kwargs.get('region', any_region())
    name = kwargs.get('name', _random_str())
    return City.objects.create(name=name, region=region)


def create_custom_location(cls, city__name=None, **kwargs):
    city = any_city(name=city__name) if city__name else any_city()
    return cls.objects.create(city=city, **kwargs)


def create_ip_range(**kwargs):
    creation_kwargs = {'start_ip': 1, 'end_ip': 2}
    creation_kwargs.update(kwargs)
    if not 'country' in creation_kwargs:
        creation_kwargs['country'] = any_country()
    return IpRange.objects.create(**creation_kwargs)
########NEW FILE########
__FILENAME__ = system
from django.test import TestCase


class IpGeoBaseSystemTest(TestCase):

    def test_whole_management_command(self):
        from django.core import management
        management.call_command('geoip_update', verbosity=0, interactive=False)
########NEW FILE########
__FILENAME__ = test_base
# -*- coding: utf-8 -*-
from django.conf import settings
from django.test import TestCase
from django.test.client import RequestFactory

from django_geoip.base import Locator
from django_geoip.models import IpRange, City
from test_app.models import MyCustomLocation

from mock import patch, Mock
from tests.factory import create_custom_location, create_ip_range


class LocatorTest(TestCase):
    def setUp(self):
        self.location_model_patcher = patch.object(settings, 'GEOIP_LOCATION_MODEL', 'test_app.models.MyCustomLocation')
        self.location_model = self.location_model_patcher.start()

        self.locator = Locator(RequestFactory().get('/'))

    def tearDown(self):
        self.location_model_patcher.stop()

    def test_get_stored_location_none(self):
        self.assertEqual(self.locator._get_stored_location(), None)

        self.locator.request.COOKIES['geoip_location_id'] = 1
        self.assertEqual(self.locator._get_stored_location(), None)

    def test_get_stored_location_ok(self):
        location = create_custom_location(MyCustomLocation, name='location1')
        self.locator.request.COOKIES['geoip_location_id'] = location.id
        self.assertEqual(self.locator._get_stored_location(), location)

    @patch('django_geoip.base.Locator._get_real_ip')
    def test_get_ip_range_none(self, mock_get_ip):
        mock_get_ip.return_value = '1.2.3.4'
        self.assertEqual(self.locator._get_ip_range(), None)

    @patch('django_geoip.base.Locator._get_real_ip')
    @patch('django_geoip.models.IpRange.objects.by_ip')
    def test_get_ip_range_ok(self, by_ip, mock_get_ip):
        mock_get_ip.return_value = '1.2.3.4'

        self.assertEqual(self.locator._get_ip_range(), by_ip.return_value)
        by_ip.assert_called_once_with('1.2.3.4')

    @patch('django_geoip.base.Locator._get_stored_location')
    def test_is_store_empty(self, mock_get_stored):
        mock_get_stored.return_value = None
        self.assertTrue(self.locator.is_store_empty())
        mock_get_stored.return_value = 1
        self.assertFalse(self.locator.is_store_empty())

    @patch('test_app.models.MyCustomLocation.get_by_ip_range')
    @patch('test_app.models.MyCustomLocation.get_default_location')
    def test_get_corresponding_location_doesnotexists(self, mock_get_default_location, mock_get_by_ip_range):
        mock_get_by_ip_range.side_effect = MyCustomLocation.DoesNotExist
        ip_range = Mock()
        self.locator._get_corresponding_location(ip_range)
        mock_get_by_ip_range.assert_called_once_with(ip_range)
        mock_get_default_location.assert_called_once()

    @patch('test_app.models.MyCustomLocation.get_by_ip_range')
    @patch('test_app.models.MyCustomLocation.get_default_location')
    def test_get_corresponding_location_exception(self, mock_get_default_location, mock_get_by_ip_range):
        mock_get_by_ip_range.side_effect = None
        ip_range = Mock()
        self.locator._get_corresponding_location(ip_range)
        mock_get_by_ip_range.assert_called_once_with(ip_range)
        mock_get_default_location.assert_called_once()

    @patch('test_app.models.MyCustomLocation.get_by_ip_range')
    @patch('test_app.models.MyCustomLocation.get_default_location')
    def test_get_corresponding_location_ok(self, mock_get_default_location, mock_get_by_ip_range):
        range = create_ip_range()
        self.locator._get_corresponding_location(range)
        mock_get_by_ip_range.assert_called_once_with(range)
        self.assertFalse(mock_get_default_location.called)

    @patch('django_geoip.base.Locator._get_stored_location')
    def test_locate_from_stored(self, mock_stored):
        self.assertEqual(self.locator.locate(), mock_stored.return_value)

    @patch('django_geoip.base.Locator._get_stored_location')
    @patch('django_geoip.base.Locator._get_corresponding_location')
    def test_locate_not_stored(self, mock_corresponding, mock_stored):
        mock_stored.return_value = None
        self.assertEqual(self.locator.locate(), mock_corresponding.return_value)
########NEW FILE########
__FILENAME__ = test_management
# coding: utf-8
from __future__ import unicode_literals
import io
import os

import requests
from mock import patch
from decimal import Decimal

from django.test import TestCase
from django.conf import settings
from django_geoip import compat

from django_geoip.management.ipgeobase import IpGeobase
from django_geoip.models import City, Region, Country, IpRange


TEST_STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))


class DowloadTest(TestCase):
    IPGEOBASE_ZIP_FILE_PATH = 'tests.zip'
    IPGEOBASE_MOCK_URL = 'http://futurecolors/mock.zip'

    @patch.object(requests, 'get')
    def test_download_unpack(self, mock):
        self.opener = mock.return_value
        self.opener.content = io.open(os.path.join(TEST_STATIC_DIR, self.IPGEOBASE_ZIP_FILE_PATH),
                                                   mode='rb').read()

        result = IpGeobase()._download_extract_archive(url=self.IPGEOBASE_MOCK_URL)

        mock.assert_called_once_with(self.IPGEOBASE_MOCK_URL)
        self.assertEqual(len(result), 2)
        self.assertTrue(result['cities'].endswith(settings.IPGEOBASE_CITIES_FILENAME))
        self.assertTrue(result['cidr'].endswith(settings.IPGEOBASE_CIDR_FILENAME))

    @patch.object(requests, 'get')
    def test_download_exception(self, mock):
        mock.side_effect = requests.exceptions.Timeout('Response timeout')
        self.assertRaises(requests.exceptions.Timeout, IpGeobase()._download_extract_archive, self.IPGEOBASE_MOCK_URL)


class ConvertTest(TestCase):
    maxDiff = None

    def test_convert_fileline_to_dict(self):
        check_against_dict = {
            'city_id': '1',
            'city_name': 'Хмельницкий',
            'region_name': 'Хмельницкая область',
            'district_name': 'Центральная Украина',
            'latitude': '49.416668',
            'longitude': '27.000000'
        }

        backend = IpGeobase()
        generator = backend._line_to_dict(
            file=io.open(os.path.join(TEST_STATIC_DIR, 'cities.txt'), encoding=settings.IPGEOBASE_FILE_ENCODING),
            field_names=settings.IPGEOBASE_CITIES_FIELDS)
        result = compat.advance_iterator(generator)
        self.assertEqual(result, check_against_dict)

    def test_process_cidr_file(self):
        check_against = {
            'cidr': [
                    {'start_ip': '33554432', 'end_ip': '34603007', 'country_id': 'FR', 'city_id': None},
                    {'start_ip': '37249024', 'end_ip': '37251071', 'country_id': 'UA', 'city_id': '1'},
                    {'start_ip': '37355520', 'end_ip': '37392639', 'country_id': 'RU', 'city_id': '2176'},
            ],
            'countries': set(['FR', 'UA', 'RU']),
            'city_country_mapping': {'2176': 'RU', '1': 'UA'}
        }
        backend = IpGeobase()
        cidr_info = backend._process_cidr_file(open(os.path.join(TEST_STATIC_DIR, 'cidr_optim.txt')))

        self.assertEqual(cidr_info['city_country_mapping'], check_against['city_country_mapping'])
        self.assertEqual(cidr_info['countries'], check_against['countries'])
        self.assertEqual(cidr_info['cidr'], check_against['cidr'])

    @patch.object(settings, 'IPGEOBASE_ALLOWED_COUNTRIES', ['RU', 'UA'])
    def test_process_cidr_file_with_allowed_countries(self):
        check_against = {
            'cidr': [
                    {'start_ip': '37249024', 'end_ip': '37251071', 'country_id': 'UA', 'city_id': '1'},
                    {'start_ip': '37355520', 'end_ip': '37392639', 'country_id': 'RU', 'city_id': '2176'},
            ],
            'countries': set(['UA', 'RU']),
            'city_country_mapping': {'2176': 'RU', '1': 'UA'}
        }
        backend = IpGeobase()
        cidr_info = backend._process_cidr_file(open(os.path.join(TEST_STATIC_DIR, 'cidr_optim.txt')))

        self.assertEqual(cidr_info['city_country_mapping'], check_against['city_country_mapping'])
        self.assertEqual(cidr_info['countries'], check_against['countries'])
        self.assertEqual(cidr_info['cidr'], check_against['cidr'])

    def test_process_cities_file(self):
        city_country_mapping = {'1': 'UA', '1057': 'RU', '2176': 'RU'}

        check_against = {
            'cities': [
                    {'region__name': 'Хмельницкая область', 'name': 'Хмельницкий',
                     'id': '1', 'latitude': Decimal('49.416668'), 'longitude': Decimal('27.000000')},
                    {'region__name': 'Кемеровская область', 'name': 'Березовский',
                     'id': '1057', 'latitude': Decimal('55.572479'), 'longitude': Decimal('86.192734')},
                    {'region__name': 'Ханты-Мансийский автономный округ', 'name': 'Мегион',
                     'id': '2176', 'latitude': Decimal('61.050400'), 'longitude': Decimal('76.113472')},
            ],
            'regions': [
                    {'name':  'Хмельницкая область', 'country__code': 'UA'},
                    {'name':  'Кемеровская область', 'country__code': 'RU'},
                    {'name':  'Ханты-Мансийский автономный округ', 'country__code': 'RU'},
            ]
        }

        backend = IpGeobase()
        cities_info = backend._process_cities_file(io.open(os.path.join(TEST_STATIC_DIR, 'cities.txt'),
                                                   encoding=settings.IPGEOBASE_FILE_ENCODING), city_country_mapping)

        self.assertEqual(cities_info['cities'], check_against['cities'])
        self.assertEqual(cities_info['regions'], check_against['regions'])

    @patch.object(settings, 'IPGEOBASE_ALLOWED_COUNTRIES', ['RU'])
    def test_process_cities_file_with_allowed_countries(self):
        city_country_mapping = {'1': 'UA', '1057': 'RU', '2176': 'RU'}

        check_against = {
            'cities': [
                    {'region__name': 'Кемеровская область', 'name': 'Березовский',
                     'id': '1057', 'longitude': Decimal('86.192734'), 'latitude': Decimal('55.572479')},
                    {'region__name': 'Ханты-Мансийский автономный округ', 'name': 'Мегион',
                     'id': '2176', 'longitude': Decimal('76.113472'), 'latitude': Decimal('61.050400')},
            ],
            'regions': [
                    {'name':  'Кемеровская область', 'country__code': 'RU'},
                    {'name':  'Ханты-Мансийский автономный округ', 'country__code': 'RU'},
            ]
        }

        backend = IpGeobase()
        cities_info = backend._process_cities_file(io.open(os.path.join(TEST_STATIC_DIR, 'cities.txt'),
                                                   encoding=settings.IPGEOBASE_FILE_ENCODING), city_country_mapping)

        self.assertEqual(cities_info['cities'], check_against['cities'])
        self.assertEqual(cities_info['regions'], check_against['regions'])

class IpGeoBaseTest(TestCase):
    maxDiff = None

    def assertCountEqual(self, first, second, msg=None):
        if compat.PY3:
            return super(IpGeoBaseTest, self).assertCountEqual(first, second, msg)
        else:
            return super(IpGeoBaseTest, self).assertItemsEqual(first, second, msg)

    def setUp(self):
        self.countries = set(['FR', 'UA', 'RU'])
        self.regions = [{'name': 'Хмельницкая область', 'country__code': 'UA'},
                {'name': 'Кемеровская область', 'country__code': 'RU'},
                {'name': 'Ханты-Мансийский автономный округ', 'country__code': 'RU'}, ]
        self.cities = [{'region__name': 'Хмельницкая область', 'name': 'Хмельницкий', 'id': 1},
                {'region__name': 'Кемеровская область', 'name': 'Березовский', 'id': 1057},
                {'region__name': 'Кемеровская область', 'name': 'Кемерово', 'id': 1058},
                {'region__name': 'Ханты-Мансийский автономный округ', 'name': 'Мегион', 'id': 2176}, ]
        self.cidr = {
            'cidr': [
                    {'start_ip': '33554432', 'end_ip': '34603007','country_id': 'FR', 'city_id': None},
                    {'start_ip': '37249024', 'end_ip': '37251071','country_id': 'UA', 'city_id': '1'},
                    {'start_ip': '37355520', 'end_ip': '37392639','country_id': 'RU', 'city_id': '2176'},
            ],
            'countries': set(['FR', 'UA', 'RU']),
            'city_country_mapping': {2176: 'RU', 1058: 'RU', 1057: 'RU', 1: 'UA'}
        }
        City.objects.all().delete()
        Region.objects.all().delete()
        Country.objects.all().delete()

    def test_update_geography_empty_data(self):
        command = IpGeobase()
        cities_info = command._update_geography(self.countries, self.regions, self.cities)

        check_against_countries = [
            {'code':'FR', 'name':'France'},
            {'code':'UA', 'name':'Ukraine'},
            {'code':'RU', 'name':'Russian Federation'}
        ]

        self.assertCountEqual(Country.objects.all().values('code', 'name'), check_against_countries)
        self.assertEqual(list(Region.objects.all().values('name', 'country__code')), self.regions)
        self.assertEqual(list(City.objects.all().values('name', 'id', 'region__name')), self.cities)

    def test_update_pre_existing_data(self):
        self.assertTrue(Country.objects.all().count() == 0)
        ua = Country.objects.create(name='Ukraine', code='UA')
        ru = Country.objects.create(name='Russia', code='RU')

        kemerovo = Region.objects.create(name='Кемеровская область', country=ru)
        City.objects.create(name='Березовский', id=1057, region=kemerovo)

        backend = IpGeobase()
        backend._update_geography(self.countries, self.regions, self.cities)

        self.assertEqual(set(Country.objects.all().values_list('code', flat=True)), self.countries)
        self.assertCountEqual(list(Region.objects.all().values('name', 'country__code')), self.regions)
        self.assertEqual(list(City.objects.all().values('name', 'id', 'region__name')), self.cities)

    def test_build_city_region_mapping(self):
        check_against_mapping = {
            1: 1,
            1057: 2,
            1058: 2,
            2176: 3,
        }
        for region in self.regions:
            Region.objects.create(name=region['name'], country_id=region['country__code'])
        for city in self.cities:
            region = Region.objects.get(name=city['region__name'])
            City.objects.create(id=city['id'], name=city['name'], region=region)

        backend = IpGeobase()
        mapping = backend._build_city_region_mapping()

        self.assertCountEqual(mapping, check_against_mapping)


    def test_update_cidr(self):
        check_against_ranges = [
            {'start_ip': 33554432, 'end_ip': 34603007, 'country_id': 'FR', 'city_id': None, 'region_id': None},
            {'start_ip': 37249024, 'end_ip': 37251071, 'country_id': 'UA', 'city_id': 1, 'region_id': 1},
            {'start_ip': 37355520, 'end_ip': 37392639, 'country_id': 'RU', 'city_id': 2176,'region_id': 3},
        ]

        backend = IpGeobase()
        for region in self.regions:
            Region.objects.create(name=region['name'], country_id=region['country__code'])
        for city in self.cities:
            region = Region.objects.get(name=city['region__name'])
            City.objects.create(id=city['id'], name=city['name'], region=region)
        backend._update_cidr(self.cidr)

        self.assertCountEqual(IpRange.objects.all().values('start_ip', 'end_ip', 'country_id', 'city_id', 'region_id'),
                              check_against_ranges)

########NEW FILE########
__FILENAME__ = test_middleware
# -*- coding: utf-8 -*-
from mock import patch

from django.conf import settings
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import unittest
from django.http import HttpResponse

import django_geoip
from django_geoip import middleware
from django_geoip.base import Locator
from django_geoip.models import City
from django_geoip.storage import LocationCookieStorage

from test_app.models import MyCustomLocation
from tests.factory import any_city, create_custom_location


class MiddlewareTest(TestCase):
    def setUp(self, *args, **kwargs):
        self.factory = RequestFactory()
        self.request = self.factory.get('/', **{'REMOTE_ADDR': '6.6.6.6'})
        self.middleware = django_geoip.middleware.LocationMiddleware()

        self.get_location_patcher = patch.object(middleware, 'get_location')
        self.get_location_patcher.start()
        self.get_location_mock = self.get_location_patcher.start()

    def tearDown(self):
        self.get_location_patcher.stop()

    def test_get_location_lazy(self):
        self.client.get('/')
        self.assertEqual(self.get_location_mock.call_count, 0)

    def test_process_request(self):
        self.get_location_mock.return_value = None
        self.middleware.process_request(self.request)
        self.assertEqual(self.request.location, None)
        self.assertEqual(self.get_location_mock.call_count, 1)

    @patch('django_geoip.storage.LocationCookieStorage.set')
    @patch.object(LocationCookieStorage, '__init__')
    def test_process_response_ok(self, mock, mock_location_set):
        mock.return_value = None
        base_response = HttpResponse()
        self.get_location_mock.return_value = mycity = any_city()
        self.middleware.process_request(self.request)
        self.middleware.process_response(self.request, base_response)
        mock.assert_called_once_with(request=self.request, response=base_response)
        # workaround simplelazyobject
        self.assertEqual(str(mycity), str(mock_location_set.call_args[1]['location']))

    @patch('django_geoip.storage.LocationCookieStorage._do_set')
    def test_process_response_empty_request_location(self, mock_do_set):
        base_response = HttpResponse()
        self.request.location = None
        self.middleware.process_response(self.request, base_response)
        self.assertFalse(mock_do_set.called)

    @patch('django_geoip.storage.LocationCookieStorage.set')
    def test_process_response_no_request_location(self, mock_set):
        base_response = HttpResponse()
        self.middleware.process_response(self.request, base_response)
        self.assertFalse(mock_set.called)


@unittest.skipIf(RequestFactory is None, "RequestFactory is avaliable from 1.3")
class GetLocationTest(unittest.TestCase):
    def setUp(self, *args, **kwargs):
        self.factory = RequestFactory()

        create_custom_location(MyCustomLocation, city__name='city1')
        self.my_location = create_custom_location(MyCustomLocation, id=200, city__name='city200')

    def tearDown(self, *args, **kwargs):
        City.objects.all().delete()

    @patch.object(settings, 'GEOIP_LOCATION_MODEL', 'test_app.models.MyCustomLocation')
    def test_get_stored_location_ok(self):
        self.factory.cookies[settings.GEOIP_COOKIE_NAME] = 200
        request = self.factory.get('/')
        self.assertEqual(Locator(request)._get_stored_location(), self.my_location)

    @patch.object(settings, 'GEOIP_LOCATION_MODEL', 'test_app.models.MyCustomLocation')
    def test_get_stored_location_none(self):
        request = self.factory.get('/')
        self.assertEqual(Locator(request)._get_stored_location(), None)
########NEW FILE########
__FILENAME__ = test_models
# -*- coding: utf-8 -*-
import struct
import socket

from django.test import TestCase
from django_geoip.models import IpRange, GeoLocationFacade

from tests import factory
from tests.factory import create_ip_range


class IpRangeTest(TestCase):

    def setUp(self):
        self.range_contains = create_ip_range(start_ip=3568355840, end_ip=3568355843)
        self.range_not_contains = create_ip_range(start_ip=3568355844, end_ip=3568355851)

    def test_manager(self):
        ip_range = IpRange.objects.by_ip('212.176.202.2')
        self.assertEqual(ip_range, self.range_contains)
        self.assertRaises(IpRange.DoesNotExist, IpRange.objects.by_ip, '127.0.0.1')

    def test_invalid_ip(self):
        self.assertRaises(IpRange.DoesNotExist, IpRange.objects.by_ip, 'wtf')

    def test_relations(self):
        self.country = factory.any_country()
        self.region = factory.any_region(country=self.country)
        self.city = factory.any_city(region=self.region)
        range = create_ip_range(start_ip=struct.unpack('!L', socket.inet_aton('43.123.56.0'))[0],
                                end_ip=struct.unpack('!L', socket.inet_aton('43.123.56.255'))[0],
                                city=self.city, region=self.region, country=self.country)

        ip_range = IpRange.objects.by_ip('43.123.56.12')
        self.assertEqual(ip_range.city, self.city)
        self.assertEqual(ip_range.city.region, self.region)
        self.assertEqual(ip_range.city.region.country, self.country)


class GeoFacadeTest(TestCase):

    def test_bad_subclass_doesnt_implement(self):

        class MyFacade(GeoLocationFacade):

            @classmethod
            def get_by_ip_range(cls, ip_range):
                return None

        self.assertRaises(TypeError, MyFacade)

    def test_facade_is_abstract_django_model(self):
        facade = GeoLocationFacade
        self.assertEqual(facade._meta.abstract, True)
########NEW FILE########
__FILENAME__ = test_storage
# -*- coding: utf-8 -*-
from datetime import datetime
from django.conf import settings
from django.test import TestCase
from django.http import HttpResponse, HttpRequest
from mock import patch, Mock
from django_geoip.storage import LocationCookieStorage, LocationDummyStorage, BaseLocationStorage
from test_app.models import MyCustomLocation
from tests.factory import create_custom_location


class BaseLocationStorageTest(TestCase):

    def setUp(self):
        self.settings_patcher = patch.object(settings, 'GEOIP_LOCATION_MODEL', 'test_app.models.MyCustomLocation')
        self.settings_patcher.start()

        self.storage = BaseLocationStorage(request=HttpRequest(), response=HttpResponse())

    def tearDown(self):
        self.settings_patcher.stop()

    def test_validate_location(self):
        self.assertFalse(self.storage._validate_location(None))
        self.assertFalse(self.storage._validate_location(Mock()))

        location = create_custom_location(MyCustomLocation)
        self.assertTrue(self.storage._validate_location(location))


class LocationCookieStorageTest(TestCase):

    def setUp(self):
        self.request = HttpRequest()
        self.request.location = Mock()

    def test_should_not_update_cookie_if_no_location_in_request(self):
        storage = LocationCookieStorage(request=HttpRequest(), response=HttpResponse())
        self.assertFalse(storage._should_update_cookie(new_value=10))

    def test_should_update_cookie_if_cookie_doesnt_exist(self):
        storage = LocationCookieStorage(request=self.request, response=HttpResponse())
        self.assertTrue(storage._should_update_cookie(new_value=10))

    def test_should_not_update_cookie_if_cookie_is_none(self):
        self.request.COOKIES[settings.GEOIP_COOKIE_NAME] = settings.GEOIP_LOCATION_EMPTY_VALUE
        storage = LocationCookieStorage(request=self.request, response=HttpResponse())
        self.assertFalse(storage._should_update_cookie(new_value=settings.GEOIP_LOCATION_EMPTY_VALUE))

    def test_should_not_update_cookie_if_cookie_is_none(self):
        self.request.COOKIES[settings.GEOIP_COOKIE_NAME] = None
        storage = LocationCookieStorage(request=self.request, response=HttpResponse())
        self.assertFalse(storage._should_update_cookie(new_value=None))

    def test_should_not_update_cookie_if_cookie_is_fresh(self):
        self.request.COOKIES[settings.GEOIP_COOKIE_NAME] = 10
        storage = LocationCookieStorage(request=self.request, response=HttpResponse())
        self.assertFalse(storage._should_update_cookie(new_value=10))

    def test_should_update_cookie_if_cookie_is_obsolete(self):
        self.request.COOKIES[settings.GEOIP_COOKIE_NAME] = 42
        storage = LocationCookieStorage(request=self.request, response=HttpResponse())
        self.assertTrue(storage._should_update_cookie(new_value=10))

    def test_should_update_cookie_if_cookie_is_empty_value(self):
        storage = LocationCookieStorage(request=self.request, response=HttpResponse())
        self.assertTrue(storage._should_update_cookie(new_value=settings.GEOIP_LOCATION_EMPTY_VALUE))

    def test_validate_location_if_cookies_is_empty_value(self):
        value = settings.GEOIP_LOCATION_EMPTY_VALUE
        storage = LocationCookieStorage(request=self.request, response=HttpResponse())
        self.assertTrue(storage._validate_location(location=value))

    @patch.object(settings, 'GEOIP_LOCATION_MODEL', 'test_app.models.MyCustomLocation')
    def test_malicious_cookie_is_no_problem(self):
        self.request.COOKIES[settings.GEOIP_COOKIE_NAME] = "wtf"
        storage = LocationCookieStorage(request=self.request, response=HttpResponse())
        self.assertEqual(storage.get(), None)

    @patch('django_geoip.storage.datetime')
    def test_do_set(self, mock):
        mock.utcnow.return_value = datetime(2030, 1, 1, 0, 0, 0)
        base_response = HttpResponse()
        storage = LocationCookieStorage(request=self.request, response=base_response)
        storage._do_set(10)
        expected = ['Set-Cookie: geoip_location_id=10', 'expires=Thu, 02-Jan-2031 00:00:00 GMT']
        self.assertEqual(base_response.cookies[settings.GEOIP_COOKIE_NAME].output().split('; ')[:2], expected)

    @patch.object(settings, 'GEOIP_COOKIE_DOMAIN', '.testserver.local')
    def test_get_cookie_domain_from_settings(self):
        storage = LocationCookieStorage(request=self.request, response=HttpResponse())
        self.assertEqual(storage.get_cookie_domain(), '.testserver.local')

    def test_get_cookie_domain_no_settings(self):
        self.request.get_host = Mock(return_value='my.localserver.tld')
        storage = LocationCookieStorage(request=self.request, response=HttpResponse())
        self.assertEqual(storage.get_cookie_domain(), None)


class LocationDummyStorageTest(TestCase):

    def setUp(self):
        self.request = HttpRequest()
        self.request.location = Mock()

    def test_get(self):
        storage = LocationDummyStorage(request=self.request, response=HttpResponse())
        self.assertEqual(storage.get(), self.request.location)

    def test_set(self):
        storage = LocationDummyStorage(request=self.request, response=HttpResponse())
        fake_location = Mock()
        storage.set(fake_location)
########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-
from django.test import TestCase
from mock import patch
from django_geoip.utils import get_mod_func, get_class


class UtilsTest(TestCase):
    def test_get_mod_func(self):
        test_hash = {
            'django.views.news.stories.story_detail': ('django.views.news.stories', 'story_detail'),
            'django': ('django', ''),
        }

        for klass, expected_result in test_hash.items():
            self.assertEqual(get_mod_func(klass), expected_result)

    @patch('django.contrib.sessions.backends.base.SessionBase')
    def test_get_class(self, SessionBase):
        """ FIXME: change to fake class"""
        test_hash = {
            'django.contrib.sessions.backends.base.SessionBase': SessionBase,
        }

        for class_string, expected_class_instance in test_hash.items():
            self.assertEqual(get_class(class_string), expected_class_instance)

        self.assertRaises(ImportError, get_class, 'django_geoip.fake')
########NEW FILE########
__FILENAME__ = test_views
# -*- coding: utf-8 -*-
from django.conf import settings
from django.test import TestCase
from test_app.models import MyCustomLocation
from mock import patch
from tests.factory import create_custom_location


class SetLocationTest(TestCase):

    def setUp(self):
        self.url = '/geoip/setlocation/'
        self.location = create_custom_location(MyCustomLocation)

        self.location_model_patcher = patch.object(settings, 'GEOIP_LOCATION_MODEL', 'test_app.models.MyCustomLocation')
        self.location_model = self.location_model_patcher.start()

    def tearDown(self):
        self.location_model_patcher.stop()

    def test_get(self):
        response = self.client.get(self.url, data={'location_id': self.location.id})
        self.assertFalse(settings.GEOIP_COOKIE_NAME in response.cookies)
        self.assertRedirects(response, 'http://testserver/')

    def test_get_or_post_next_url(self):
        for method in ['get', 'post']:
            method_call = getattr(self.client, method)
            response = method_call(self.url, data={'next': '/hello/',
                                                   'location_id': self.location.id})
            self.assertRedirects(response, 'http://testserver/hello/')

    def test_post_ok(self):
        response = self.client.post(self.url, data={'location_id': self.location.id})
        self.assertEqual(response.cookies[settings.GEOIP_COOKIE_NAME].value, str(self.location.id))
        self.assertRedirects(response, 'http://testserver/')

    def test_alternative_post_name(self):
        response = self.client.post(self.url, data={'location': self.location.id})
        self.assertEqual(response.cookies[settings.GEOIP_COOKIE_NAME].value, str(self.location.id))
        self.assertRedirects(response, 'http://testserver/')

    def test_post_fake_location(self):
        response = self.client.post(self.url, data={'location_id': self.location.id+1})
        self.assertFalse(settings.GEOIP_COOKIE_NAME in response.cookies)
        self.assertRedirects(response, 'http://testserver/')

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django_geoip.models import GeoLocationFacade, City


class MyCustomLocation(GeoLocationFacade):
    name = models.CharField(max_length=100)
    city = models.OneToOneField(City, related_name='my_custom_location')

    @classmethod
    def get_by_ip_range(cls, ip_range):
        return ip_range.city.my_custom_location

    @classmethod
    def get_default_location(cls):
        return cls.objects.get(pk=1)

    @classmethod
    def get_available_locations(cls):
        return cls.objects.all()

    def __repr__(self):
        return 'MyCustomLocation(id={0}, city={1})'.format(self.pk, self.city.name)
########NEW FILE########
__FILENAME__ = test_settings
import django

if django.VERSION[:2] >= (1, 3):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        },
    }
else:
    DATABASE_ENGINE = 'sqlite3'

SECRET_KEY = '_'
ROOT_URLCONF = 'test_app.urls'
INSTALLED_APPS = ('django_geoip', 'test_app')

if django.VERSION[:2] < (1, 6):
    TEST_RUNNER = 'discover_runner.DiscoverRunner'
########NEW FILE########
__FILENAME__ = urls
# coding: utf-8
try:
    from django.conf.urls import patterns, include
except ImportError:
    from django.conf.urls.defaults import patterns, include
from django.http import HttpResponse
from django_geoip.views import set_location


def index_view(request):
    return HttpResponse()


urlpatterns = patterns('',
    ('^$', index_view),
    (r'^geoip/', include('django_geoip.urls')),
    ('^hello/$', index_view),
)

########NEW FILE########
