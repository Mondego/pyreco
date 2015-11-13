__FILENAME__ = conf
import django.conf


class AppSettings(django.conf.BaseSettings):
    """
    A holder for app-specific default settings that allows overriding via
    the project's settings.
    """

    def __getattribute__(self, attr):
        if attr == attr.upper():
            try:
                return getattr(django.conf.settings, attr)
            except AttributeError:
                pass
        return super(AppSettings, self).__getattribute__(attr)


class Settings(AppSettings):
    COUNTRIES_FLAG_URL = 'flags/{code}.gif'
    """
    The URL for a flag.

    It can either be relative to the static url, or an absolute url.

    The location is parsed using Python's string formatting and is passed the
    following arguments:

        * code
        * code_upper

    For example: ``COUNTRIES_FLAG_URL = 'flags/16x10/{code_upper}.png'``
    """

    COUNTRIES_OVERRIDE = {}
    """
    A dictionary of names to override the defaults.

    Note that you will need to handle translation of customised country names.

    Setting a country's name to ``None`` will exclude it from the country list.
    For example::

        COUNTRIES_OVERRIDE = {
            'NZ': _('Middle Earth'),
            'AU': None
        }
    """


settings = Settings()

########NEW FILE########
__FILENAME__ = data
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import glob
import os

try:
    from django.utils.translation import ugettext_lazy as _
except ImportError:
    # Allows this module to be executed without Django installed.
    _ = lambda x: x

# Nicely titled (and translatable) country names.
COUNTRIES = {
    "AF": _("Afghanistan"),
    "AX": _("Åland Islands"),
    "AL": _("Albania"),
    "DZ": _("Algeria"),
    "AS": _("American Samoa"),
    "AD": _("Andorra"),
    "AO": _("Angola"),
    "AI": _("Anguilla"),
    "AQ": _("Antarctica"),
    "AG": _("Antigua and Barbuda"),
    "AR": _("Argentina"),
    "AM": _("Armenia"),
    "AW": _("Aruba"),
    "AU": _("Australia"),
    "AT": _("Austria"),
    "AZ": _("Azerbaijan"),
    "BS": _("Bahamas"),
    "BH": _("Bahrain"),
    "BD": _("Bangladesh"),
    "BB": _("Barbados"),
    "BY": _("Belarus"),
    "BE": _("Belgium"),
    "BZ": _("Belize"),
    "BJ": _("Benin"),
    "BM": _("Bermuda"),
    "BT": _("Bhutan"),
    "BO": _("Bolivia, Plurinational State of"),
    "BQ": _("Bonaire, Sint Eustatius and Saba"),
    "BA": _("Bosnia and Herzegovina"),
    "BW": _("Botswana"),
    "BV": _("Bouvet Island"),
    "BR": _("Brazil"),
    "IO": _("British Indian Ocean Territory"),
    "BN": _("Brunei Darussalam"),
    "BG": _("Bulgaria"),
    "BF": _("Burkina Faso"),
    "BI": _("Burundi"),
    "KH": _("Cambodia"),
    "CM": _("Cameroon"),
    "CA": _("Canada"),
    "CV": _("Cape Verde"),
    "KY": _("Cayman Islands"),
    "CF": _("Central African Republic"),
    "TD": _("Chad"),
    "CL": _("Chile"),
    "CN": _("China"),
    "CX": _("Christmas Island"),
    "CC": _("Cocos (Keeling) Islands"),
    "CO": _("Colombia"),
    "KM": _("Comoros"),
    "CG": _("Congo"),
    "CD": _("Congo (the Democratic Republic of the)"),
    "CK": _("Cook Islands"),
    "CR": _("Costa Rica"),
    "CI": _("Côte d'Ivoire"),
    "HR": _("Croatia"),
    "CU": _("Cuba"),
    "CW": _("Curaçao"),
    "CY": _("Cyprus"),
    "CZ": _("Czech Republic"),
    "DK": _("Denmark"),
    "DJ": _("Djibouti"),
    "DM": _("Dominica"),
    "DO": _("Dominican Republic"),
    "EC": _("Ecuador"),
    "EG": _("Egypt"),
    "SV": _("El Salvador"),
    "GQ": _("Equatorial Guinea"),
    "ER": _("Eritrea"),
    "EE": _("Estonia"),
    "ET": _("Ethiopia"),
    "FK": _("Falkland Islands  [Malvinas]"),
    "FO": _("Faroe Islands"),
    "FJ": _("Fiji"),
    "FI": _("Finland"),
    "FR": _("France"),
    "GF": _("French Guiana"),
    "PF": _("French Polynesia"),
    "TF": _("French Southern Territories"),
    "GA": _("Gabon"),
    "GM": _("Gambia (The)"),
    "GE": _("Georgia"),
    "DE": _("Germany"),
    "GH": _("Ghana"),
    "GI": _("Gibraltar"),
    "GR": _("Greece"),
    "GL": _("Greenland"),
    "GD": _("Grenada"),
    "GP": _("Guadeloupe"),
    "GU": _("Guam"),
    "GT": _("Guatemala"),
    "GG": _("Guernsey"),
    "GN": _("Guinea"),
    "GW": _("Guinea-Bissau"),
    "GY": _("Guyana"),
    "HT": _("Haiti"),
    "HM": _("Heard Island and McDonald Islands"),
    "VA": _("Holy See  [Vatican City State]"),
    "HN": _("Honduras"),
    "HK": _("Hong Kong"),
    "HU": _("Hungary"),
    "IS": _("Iceland"),
    "IN": _("India"),
    "ID": _("Indonesia"),
    "IR": _("Iran (the Islamic Republic of)"),
    "IQ": _("Iraq"),
    "IE": _("Ireland"),
    "IM": _("Isle of Man"),
    "IL": _("Israel"),
    "IT": _("Italy"),
    "JM": _("Jamaica"),
    "JP": _("Japan"),
    "JE": _("Jersey"),
    "JO": _("Jordan"),
    "KZ": _("Kazakhstan"),
    "KE": _("Kenya"),
    "KI": _("Kiribati"),
    "KP": _("Korea (the Democratic People's Republic of)"),
    "KR": _("Korea (the Republic of)"),
    "KW": _("Kuwait"),
    "KG": _("Kyrgyzstan"),
    "LA": _("Lao People's Democratic Republic"),
    "LV": _("Latvia"),
    "LB": _("Lebanon"),
    "LS": _("Lesotho"),
    "LR": _("Liberia"),
    "LY": _("Libya"),
    "LI": _("Liechtenstein"),
    "LT": _("Lithuania"),
    "LU": _("Luxembourg"),
    "MO": _("Macao"),
    "MK": _("Macedonia (the former Yugoslav Republic of)"),
    "MG": _("Madagascar"),
    "MW": _("Malawi"),
    "MY": _("Malaysia"),
    "MV": _("Maldives"),
    "ML": _("Mali"),
    "MT": _("Malta"),
    "MH": _("Marshall Islands"),
    "MQ": _("Martinique"),
    "MR": _("Mauritania"),
    "MU": _("Mauritius"),
    "YT": _("Mayotte"),
    "MX": _("Mexico"),
    "FM": _("Micronesia (the Federated States of)"),
    "MD": _("Moldova (the Republic of)"),
    "MC": _("Monaco"),
    "MN": _("Mongolia"),
    "ME": _("Montenegro"),
    "MS": _("Montserrat"),
    "MA": _("Morocco"),
    "MZ": _("Mozambique"),
    "MM": _("Myanmar"),
    "NA": _("Namibia"),
    "NR": _("Nauru"),
    "NP": _("Nepal"),
    "NL": _("Netherlands"),
    "NC": _("New Caledonia"),
    "NZ": _("New Zealand"),
    "NI": _("Nicaragua"),
    "NE": _("Niger"),
    "NG": _("Nigeria"),
    "NU": _("Niue"),
    "NF": _("Norfolk Island"),
    "MP": _("Northern Mariana Islands"),
    "NO": _("Norway"),
    "OM": _("Oman"),
    "PK": _("Pakistan"),
    "PW": _("Palau"),
    "PS": _("Palestine, State of"),
    "PA": _("Panama"),
    "PG": _("Papua New Guinea"),
    "PY": _("Paraguay"),
    "PE": _("Peru"),
    "PH": _("Philippines"),
    "PN": _("Pitcairn"),
    "PL": _("Poland"),
    "PT": _("Portugal"),
    "PR": _("Puerto Rico"),
    "QA": _("Qatar"),
    "RE": _("Réunion"),
    "RO": _("Romania"),
    "RU": _("Russian Federation"),
    "RW": _("Rwanda"),
    "BL": _("Saint Barthélemy"),
    "SH": _("Saint Helena, Ascension and Tristan da Cunha"),
    "KN": _("Saint Kitts and Nevis"),
    "LC": _("Saint Lucia"),
    "MF": _("Saint Martin (French part)"),
    "PM": _("Saint Pierre and Miquelon"),
    "VC": _("Saint Vincent and the Grenadines"),
    "WS": _("Samoa"),
    "SM": _("San Marino"),
    "ST": _("Sao Tome and Principe"),
    "SA": _("Saudi Arabia"),
    "SN": _("Senegal"),
    "RS": _("Serbia"),
    "SC": _("Seychelles"),
    "SL": _("Sierra Leone"),
    "SG": _("Singapore"),
    "SX": _("Sint Maarten (Dutch part)"),
    "SK": _("Slovakia"),
    "SI": _("Slovenia"),
    "SB": _("Solomon Islands"),
    "SO": _("Somalia"),
    "ZA": _("South Africa"),
    "GS": _("South Georgia and the South Sandwich Islands"),
    "SS": _("South Sudan"),
    "ES": _("Spain"),
    "LK": _("Sri Lanka"),
    "SD": _("Sudan"),
    "SR": _("Suriname"),
    "SJ": _("Svalbard and Jan Mayen"),
    "SZ": _("Swaziland"),
    "SE": _("Sweden"),
    "CH": _("Switzerland"),
    "SY": _("Syrian Arab Republic"),
    "TW": _("Taiwan (Province of China)"),
    "TJ": _("Tajikistan"),
    "TZ": _("Tanzania, United Republic of"),
    "TH": _("Thailand"),
    "TL": _("Timor-Leste"),
    "TG": _("Togo"),
    "TK": _("Tokelau"),
    "TO": _("Tonga"),
    "TT": _("Trinidad and Tobago"),
    "TN": _("Tunisia"),
    "TR": _("Turkey"),
    "TM": _("Turkmenistan"),
    "TC": _("Turks and Caicos Islands"),
    "TV": _("Tuvalu"),
    "UG": _("Uganda"),
    "UA": _("Ukraine"),
    "AE": _("United Arab Emirates"),
    "GB": _("United Kingdom"),
    "US": _("United States"),
    "UM": _("United States Minor Outlying Islands"),
    "UY": _("Uruguay"),
    "UZ": _("Uzbekistan"),
    "VU": _("Vanuatu"),
    "VE": _("Venezuela, Bolivarian Republic of"),
    "VN": _("Viet Nam"),
    "VG": _("Virgin Islands (British)"),
    "VI": _("Virgin Islands (U.S.)"),
    "WF": _("Wallis and Futuna"),
    "EH": _("Western Sahara"),
    "YE": _("Yemen"),
    "ZM": _("Zambia"),
    "ZW": _("Zimbabwe"),
}


def self_generate(output_filename, filename='iso3166-1.csv'):
    """
    The following code can be used for self-generation of this file.

    It requires a UTF-8 CSV file containing the short ISO name and two letter
    country code as the first two columns.
    """
    import csv
    import re
    countries = []
    with open(filename, 'rb') as csv_file:
        for row in csv.reader(csv_file):
            name = row[0].decode('utf-8').rstrip('*')
            name = re.sub(r'\(the\)', '', name)
            if name:
                countries.append((name, row[1].decode('utf-8')))
    with open(__file__, 'r') as source_file:
        contents = source_file.read()
    bits = re.match(
        '(.*\nCOUNTRIES = \{\n)(.*)(\n\}.*)', contents, re.DOTALL).groups()
    country_list = []
    for name, code in countries:
        name = name.replace('"', r'\"').strip()
        country_list.append(
            '    "{code}": _("{name}"),'.format(name=name, code=code))
    content = bits[0]
    content += '\n'.join(country_list).encode('utf-8')
    content += bits[2]
    with open(output_filename, 'wb') as output_file:
        output_file.write(content)
    return countries


def check_flags():
    files = {}
    this_dir = os.path.dirname(__file__)
    for path in glob.glob(os.path.join(this_dir, 'static', 'flags', '*.gif')):
        files[os.path.basename(os.path.splitext(path)[0]).upper()] = path

    flags_missing = []
    for code in COUNTRIES:
        if code not in files:
            flags_missing.append(code)
    if flags_missing:
        flags_missing.sort()
        print("The following country codes are missing a flag:")
        for code in flags_missing:
            print("  {} ({})".format(code, COUNTRIES[code]))
    else:
        print("All country codes have flags. :)")

    code_missing = []
    for code, path in files.items():
        if code not in COUNTRIES:
            code_missing.append(path)
    if code_missing:
        code_missing.sort()
        print("")
        print("The following flags don't have a matching country code:")
        for path in code_missing:
            print("  {}".format(path))


if __name__ == '__main__':
    countries = self_generate(__file__)
    print('Wrote {0} countries.'.format(len(countries)))

    # Check flag static files:
    print("")
    check_flags()

########NEW FILE########
__FILENAME__ = fields
from __future__ import unicode_literals

try:
    from urllib import parse as urlparse
except ImportError:
    import urlparse   # Python 2

from django.db.models.fields import CharField
from django.utils.encoding import force_text, python_2_unicode_compatible

from django_countries import countries, ioc_data
from django_countries.conf import settings


@python_2_unicode_compatible
class Country(object):
    def __init__(self, code, flag_url):
        self.code = code
        self.flag_url = flag_url

    def __str__(self):
        return force_text(self.code or '')

    def __eq__(self, other):
        return force_text(self) == force_text(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(force_text(self))

    def __repr__(self):
        return "{}(code={}, flag_url={})".format(
            self.__class__.__name__, repr(self.code), repr(self.flag_url))

    def __bool__(self):
        return bool(self.code)

    __nonzero__ = __bool__   # Python 2 compatibility.

    def __len__(self):
        return len(force_text(self))

    @property
    def name(self):
        return countries.name(self.code)

    @property
    def flag(self):
        if not self.code:
            return ''
        url = self.flag_url.format(
            code_upper=self.code, code=self.code.lower())
        return urlparse.urljoin(settings.STATIC_URL, url)

    @staticmethod
    def country_from_ioc(ioc_code, flag_url=''):
        code = ioc_data.IOC_TO_ISO.get(ioc_code, '')
        if code == '':
            return None
        return Country(code, flag_url=flag_url)

    @property
    def ioc_code(self):
        if not self.code:
            return ''
        return ioc_data.ISO_TO_IOC.get(self.code, '')


class CountryDescriptor(object):
    """
    A descriptor for country fields on a model instance. Returns a Country when
    accessed so you can do things like::

        >>> from people import Person
        >>> person = Person.object.get(name='Chris')

        >>> person.country.name
        u'New Zealand'

        >>> person.country.flag
        '/static/flags/nz.gif'
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, instance=None, owner=None):
        if instance is None:
            raise AttributeError(
                "The '%s' attribute can only be accessed from %s instances."
                % (self.field.name, owner.__name__))
        return Country(
            code=instance.__dict__[self.field.name],
            flag_url=self.field.countries_flag_url or
            settings.COUNTRIES_FLAG_URL)

    def __set__(self, instance, value):
        if value is not None:
            value = force_text(value)
        instance.__dict__[self.field.name] = value


class CountryField(CharField):
    """
    A country field for Django models that provides all ISO 3166-1 countries as
    choices.
    """
    descriptor_class = CountryDescriptor

    def __init__(self, *args, **kwargs):
        self.countries_flag_url = kwargs.pop('countries_flag_url', None)
        kwargs.update({
            'max_length': 2,
            'choices': countries,
        })
        super(CharField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"

    def contribute_to_class(self, cls, name):
        super(CountryField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, self.descriptor_class(self))

    def get_prep_lookup(self, lookup_type, value):
        if hasattr(value, 'code'):
            value = value.code
        return super(CountryField, self).get_prep_lookup(lookup_type, value)

    def pre_save(self, *args, **kwargs):
        "Returns field's value just before saving."
        value = super(CharField, self).pre_save(*args, **kwargs)
        return self.get_prep_value(value)

    def get_prep_value(self, value):
        "Returns field's value prepared for saving into a database."
        # Convert the Country to unicode for database insertion.
        if value is None:
            return None
        return force_text(value)


# If south is installed, ensure that CountryField will be introspected just
# like a normal CharField.
try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ['^django_countries\.fields\.CountryField'])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = ioc_data
IOC_TO_ISO = {
    'AFG': 'AF',
    'ALB': 'AL',
    'ALG': 'DZ',
    'AND': 'AD',
    'ANG': 'AO',
    'ANT': 'AG',
    'ARG': 'AR',
    'ARM': 'AM',
    'ARU': 'AW',
    'ASA': 'AS',
    'AUS': 'AU',
    'AUT': 'AT',
    'AZE': 'AZ',
    'BAH': 'BS',
    'BAN': 'BD',
    'BAR': 'BB',
    'BDI': 'BI',
    'BEL': 'BE',
    'BEN': 'BJ',
    'BER': 'BM',
    'BHU': 'BT',
    'BIH': 'BA',
    'BIZ': 'BZ',
    'BLR': 'BY',
    'BOL': 'BO',
    'BOT': 'BW',
    'BRA': 'BR',
    'BRN': 'BH',
    'BRU': 'BN',
    'BUL': 'BG',
    'BUR': 'BF',
    'CAF': 'CF',
    'CAM': 'KH',
    'CAN': 'CA',
    'CAY': 'KY',
    'CGO': 'CG',
    'CHA': 'TD',
    'CHI': 'CL',
    'CHN': 'CN',
    'CIV': 'CI',
    'CMR': 'CM',
    'COD': 'CD',
    'COK': 'CK',
    'COL': 'CO',
    'COM': 'KM',
    'CPV': 'CV',
    'CRC': 'CR',
    'CRO': 'HR',
    'CUB': 'CU',
    'CYP': 'CY',
    'CZE': 'CZ',
    'DEN': 'DK',
    'DJI': 'DJ',
    'DMA': 'DM',
    'DOM': 'DO',
    'ECU': 'EC',
    'EGY': 'EG',
    'ERI': 'ER',
    'ESA': 'SV',
    'ESP': 'ES',
    'EST': 'EE',
    'ETH': 'ET',
    'FIJ': 'FJ',
    'FIN': 'FI',
    'FRA': 'FR',
    'FSM': 'FM',
    'GAB': 'GA',
    'GAM': 'GM',
    'GBR': 'GB',
    'GBS': 'GW',
    'GEO': 'GE',
    'GEQ': 'GQ',
    'GER': 'DE',
    'GHA': 'GH',
    'GRE': 'GR',
    'GRN': 'GD',
    'GUA': 'GT',
    'GUI': 'GN',
    'GUM': 'GU',
    'GUY': 'GY',
    'HAI': 'HT',
    'HKG': 'HK',
    'HON': 'HN',
    'HUN': 'HU',
    'INA': 'ID',
    'IND': 'IN',
    'IRI': 'IR',
    'IRL': 'IE',
    'IRQ': 'IQ',
    'ISL': 'IS',
    'ISR': 'IL',
    'ISV': 'VI',
    'ITA': 'IT',
    'IVB': 'VG',
    'JAM': 'JM',
    'JOR': 'JO',
    'JPN': 'JP',
    'KAZ': 'KZ',
    'KEN': 'KE',
    'KGZ': 'KG',
    'KIR': 'KI',
    'KOR': 'KP',
    'KSA': 'SA',
    'KUW': 'KW',
    'LAO': 'LA',
    'LAT': 'LV',
    'LBA': 'LY',
    'LBR': 'LR',
    'LCA': 'LC',
    'LES': 'LS',
    'LIB': 'LB',
    'LIE': 'LI',
    'LTU': 'LT',
    'LUX': 'LU',
    'MAD': 'MG',
    'MAR': 'MA',
    'MAS': 'MY',
    'MAW': 'MW',
    'MDA': 'MD',
    'MDV': 'MV',
    'MEX': 'MX',
    'MGL': 'MN',
    'MHL': 'MH',
    'MKD': 'MK',
    'MLI': 'ML',
    'MLT': 'MT',
    'MNE': 'ME',
    'MON': 'MC',
    'MOZ': 'MZ',
    'MRI': 'MU',
    'MTN': 'MR',
    'MYA': 'MM',
    'NAM': 'NA',
    'NCA': 'NI',
    'NED': 'NL',
    'NEP': 'NP',
    'NGR': 'NG',
    'NIG': 'NE',
    'NOR': 'NO',
    'NRU': 'NR',
    'NZL': 'NZ',
    'OMA': 'OM',
    'PAK': 'PK',
    'PAN': 'PA',
    'PAR': 'PY',
    'PER': 'PE',
    'PHI': 'PH',
    'PLE': 'PS',
    'PLW': 'PW',
    'PNG': 'PG',
    'POL': 'PL',
    'POR': 'PT',
    'PRK': 'KR',
    'PUR': 'PR',
    'QAT': 'QA',
    'ROU': 'RO',
    'RSA': 'ZA',
    'RUS': 'RU',
    'RWA': 'RW',
    'SAM': 'WS',
    'SEN': 'SN',
    'SEY': 'SC',
    'SIN': 'SG',
    'SKN': 'KN',
    'SLE': 'SL',
    'SLO': 'SI',
    'SMR': 'SM',
    'SOL': 'SB',
    'SOM': 'SO',
    'SRB': 'RS',
    'SRI': 'LK',
    'STP': 'ST',
    'SUD': 'SD',
    'SUI': 'CH',
    'SUR': 'SR',
    'SVK': 'SK',
    'SWE': 'SE',
    'SWZ': 'SZ',
    'SYR': 'SY',
    'TAN': 'TZ',
    'TGA': 'TO',
    'THA': 'TH',
    'TJK': 'TJ',
    'TKM': 'TM',
    'TLS': 'TL',
    'TOG': 'TG',
    'TPE': 'TW',
    'TTO': 'TT',
    'TUN': 'TN',
    'TUR': 'TR',
    'TUV': 'TV',
    'UAE': 'AE',
    'UGA': 'UG',
    'UKR': 'UA',
    'URU': 'UY',
    'USA': 'US',
    'UZB': 'UZ',
    'VAN': 'VU',
    'VEN': 'VE',
    'VIE': 'VN',
    'VIN': 'VC',
    'YEM': 'YE',
    'ZAM': 'ZM',
    'ZIM': 'ZW',
}

ISO_TO_IOC = dict((iso, ioc) for ioc, iso in IOC_TO_ISO.items())


def check_ioc_countries():
    """
    Check if all IOC codes map to ISO codes correctly
    """
    from django_countries.data import COUNTRIES

    print("Checking if all IOC codes map correctly")
    for key in ISO_TO_IOC.keys():
        assert COUNTRIES.get(key, '') != '', 'No ISO code for %s' % key
    print("Finished checking IOC codes")

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django_countries.fields import CountryField


class Person(models.Model):
    name = models.CharField(max_length=50)
    country = CountryField()
    other_country = CountryField(
        blank=True, countries_flag_url='//flags.example.com/{code}.gif')


class AllowNull(models.Model):
    country = CountryField(null=True)

########NEW FILE########
__FILENAME__ = settings
SECRET_KEY = 'test'

INSTALLED_APPS = (
    'django_countries',
    'django_countries.tests',
)

DATABASES = {
    'default': {'ENGINE': 'django.db.backends.sqlite3'}
}

STATIC_URL = '/static-assets/'

########NEW FILE########
__FILENAME__ = test_countries
from __future__ import unicode_literals
from django.test import TestCase

from django_countries import countries


class TestCountriesObject(TestCase):
    EXPECTED_COUNTRY_COUNT = 249

    def setUp(self):
        del countries.countries

    def tearDown(self):
        del countries.countries

    def test_countries_len(self):
        self.assertEqual(len(countries), self.EXPECTED_COUNTRY_COUNT)

    def test_countries_custom_removed_len(self):
        with self.settings(COUNTRIES_OVERRIDE={'AU': None}):
            self.assertEqual(len(countries), self.EXPECTED_COUNTRY_COUNT - 1)

    def test_countries_custom_added_len(self):
        with self.settings(COUNTRIES_OVERRIDE={'XX': 'Neverland'}):
            self.assertEqual(len(countries), self.EXPECTED_COUNTRY_COUNT + 1)

    def test_countries_custom_ugettext_evaluation(self):

        class FakeLazyUGetText(object):

            def __bool__(self):
                raise ValueError("Can't evaluate lazy_ugettext yet")

            __nonzero__ = __bool__

        with self.settings(COUNTRIES_OVERRIDE={'AU': FakeLazyUGetText()}):
            countries.countries

########NEW FILE########
__FILENAME__ = test_fields
from __future__ import unicode_literals
from django.test import TestCase
from django.utils.encoding import force_text

from django_countries import fields
from django_countries.tests.models import Person, AllowNull


class TestCountryField(TestCase):

    def test_logic(self):
        person = Person(name='Chris Beaven', country='NZ')

        self.assertEqual(person.country, 'NZ')
        self.assertNotEqual(person.country, 'ZZ')

        self.assertTrue(person.country)
        person.country = ''
        self.assertFalse(person.country)

    def test_text(self):
        person = Person(name='Chris Beaven', country='NZ')
        self.assertEqual(force_text(person.country), 'NZ')

    def test_name(self):
        person = Person(name='Chris Beaven', country='NZ')
        self.assertEqual(person.country.name, u'New Zealand')

    def test_flag(self):
        person = Person(name='Chris Beaven', country='NZ')
        self.assertEqual(person.country.flag, '/static-assets/flags/nz.gif')

    def test_custom_field_flag_url(self):
        person = Person(name='Chris Beaven', country='NZ', other_country='US')
        self.assertEqual(
            person.other_country.flag, '//flags.example.com/us.gif')

    def test_COUNTRIES_FLAG_URL_setting(self):
        # Custom relative url
        person = Person(name='Chris Beaven', country='NZ')
        with self.settings(COUNTRIES_FLAG_URL='img/flag-{code_upper}.png'):
            self.assertEqual(
                person.country.flag, '/static-assets/img/flag-NZ.png')
        # Custom absolute url
        with self.settings(COUNTRIES_FLAG_URL='https://flags.example.com/'
                           '{code_upper}.PNG'):
            self.assertEqual(
                person.country.flag, 'https://flags.example.com/NZ.PNG')

    def test_blank(self):
        person = Person.objects.create(name='The Outsider', country=None)
        self.assertEqual(person.country, '')

        person = Person.objects.get(pk=person.pk)
        self.assertEqual(person.country, '')

    def test_len(self):
        person = Person(name='Chris Beaven', country='NZ')
        self.assertEqual(len(person.country), 2)

        person = Person(name='The Outsider', country=None)
        self.assertEqual(len(person.country), 0)

    def test_lookup_text(self):
        Person.objects.create(name='Chris Beaven', country='NZ')
        Person.objects.create(name='Pavlova', country='NZ')
        Person.objects.create(name='Killer everything', country='AU')

        lookup = Person.objects.filter(country='NZ')
        names = lookup.order_by('name').values_list('name', flat=True)
        self.assertEqual(list(names), ['Chris Beaven', 'Pavlova'])

    def test_lookup_country(self):
        Person.objects.create(name='Chris Beaven', country='NZ')
        Person.objects.create(name='Pavlova', country='NZ')
        Person.objects.create(name='Killer everything', country='AU')

        oz = fields.Country(code='AU', flag_url='')
        lookup = Person.objects.filter(country=oz)
        names = lookup.values_list('name', flat=True)
        self.assertEqual(list(names), ['Killer everything'])

    def test_save_empty_country(self):
        Person.objects.create(name='The Outsider', country=None)
        AllowNull.objects.create(country=None)


class TestCountryObject(TestCase):

    def test_hash(self):
        country = fields.Country(code='XX', flag_url='')
        self.assertEqual(hash(country), hash('XX'))

    def test_repr(self):
        country = fields.Country(code='XX', flag_url='')
        self.assertEqual(
            repr(country),
            'Country(code={}, flag_url={})'.format(repr('XX'), repr('')))

    def test_flag_on_empty_code(self):
        country = fields.Country(code='', flag_url='')
        self.assertEqual(country.flag, '')

    def test_ioc_code(self):
        country = fields.Country(code='NL', flag_url='')
        self.assertEqual(country.ioc_code, 'NED')

    def test_country_from_ioc_code(self):
        country = fields.Country.country_from_ioc('NED')
        self.assertEqual(country, fields.Country('NL', flag_url=''))

    def test_country_from_blank_ioc_code(self):
        country = fields.Country.country_from_ioc('')
        self.assertIsNone(country)

    def test_country_from_nonexistence_ioc_code(self):
        country = fields.Country.country_from_ioc('XXX')
        self.assertIsNone(country)

########NEW FILE########
__FILENAME__ = test_settings
from __future__ import unicode_literals
from django.test import TestCase

from django_countries import countries


class TestSettings(TestCase):

    def setUp(self):
        del countries.countries

    def tearDown(self):
        del countries.countries

    def test_override_additional(self):
        with self.settings(COUNTRIES_OVERRIDE={'XX': 'New'}):
            self.assertEqual(countries.name('XX'), 'New')

    def test_override_replace(self):
        with self.settings(COUNTRIES_OVERRIDE={'NZ': 'Middle Earth'}):
            self.assertEqual(countries.name('NZ'), 'Middle Earth')

    def test_override_remove(self):
        with self.settings(COUNTRIES_OVERRIDE={'AU': None}):
            self.assertNotIn('AU', countries.countries)
            self.assertEqual(countries.name('AU'), '')

########NEW FILE########
