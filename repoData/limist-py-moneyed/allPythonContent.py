__FILENAME__ = classes
# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import unicode_literals

from decimal import Decimal, ROUND_DOWN

# Default, non-existent, currency
DEFAULT_CURRENCY_CODE = 'XYZ'


class Currency(object):
    """
    A Currency represents a form of money issued by governments, and
    used in one or more states/countries.  A Currency instance
    encapsulates the related data of: the ISO currency/numeric code, a
    canonical name, countries the currency is used in, and an exchange
    rate - the last remains unimplemented however.
    """

    def __init__(self, code='', numeric='999', name='', countries=[]):
        self.code = code
        self.countries = countries
        self.name = name
        self.numeric = numeric

    def __repr__(self):
        return self.code


class MoneyComparisonError(TypeError):
    # This exception was needed often enough to merit its own
    # Exception class.

    def __init__(self, other):
        assert not isinstance(other, Money)
        self.other = other

    def __str__(self):
        # Note: at least w/ Python 2.x, use __str__, not __unicode__.
        return "Cannot compare instances of Money and %s" \
               % self.other.__class__.__name__


class CurrencyDoesNotExist(Exception):

    def __init__(self, code):
        super(CurrencyDoesNotExist, self).__init__(
            "No currency with code %s is defined." % code)


class Money(object):
    """
    A Money instance is a combination of data - an amount and a
    currency - along with operators that handle the semantics of money
    operations in a better way than just dealing with raw Decimal or
    ($DEITY forbid) floats.
    """

    def __init__(self, amount=Decimal('0.0'), currency=DEFAULT_CURRENCY_CODE):
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        self.amount = amount

        if not isinstance(currency, Currency):
            currency = get_currency(str(currency).upper())
        self.currency = currency

    def __repr__(self):
        return "%s %s" % (self.amount.to_integral_value(ROUND_DOWN),
                          self.currency)

    def __unicode__(self):
        from moneyed.localization import format_money
        return format_money(self)

    def __str__(self):
        from moneyed.localization import format_money
        return format_money(self)

    def __pos__(self):
        return Money(
            amount=self.amount,
            currency=self.currency)

    def __neg__(self):
        return Money(
            amount= -self.amount,
            currency=self.currency)

    def __add__(self, other):
        if not isinstance(other, Money):
            raise TypeError('Cannot add or subtract a ' +
                            'Money and non-Money instance.')
        if self.currency == other.currency:
            return Money(
                amount=self.amount + other.amount,
                currency=self.currency)

        raise TypeError('Cannot add or subtract two Money ' +
                        'instances with different currencies.')

    def __sub__(self, other):
        return self.__add__(-other)

    def __mul__(self, other):
        if isinstance(other, Money):
            raise TypeError('Cannot multiply two Money instances.')
        else:
            return Money(
                amount=(self.amount * Decimal(str(other))),
                currency=self.currency)

    def __truediv__(self, other):
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise TypeError('Cannot divide two different currencies.')
            return self.amount / other.amount
        else:
            return Money(
                amount=self.amount / Decimal(str(other)),
                currency=self.currency)

    def __abs__(self):
        return Money(
            amount=abs(self.amount),
            currency=self.currency)

    def __rmod__(self, other):
        """
        Calculate percentage of an amount.  The left-hand side of the
        operator must be a numeric value.

        Example:
        >>> money = Money(200, 'USD')
        >>> 5 % money
        USD 10.00
        """
        if isinstance(other, Money):
            raise TypeError('Invalid __rmod__ operation')
        else:
            return Money(
                amount=(Decimal(str(other)) * self.amount / 100),
                currency=self.currency)

    __radd__ = __add__
    __rsub__ = __sub__
    __rmul__ = __mul__
    __rtruediv__ = __truediv__

    # _______________________________________
    # Override comparison operators
    def __eq__(self, other):
        return isinstance(other, Money)\
               and (self.amount == other.amount) \
               and (self.currency == other.currency)

    def __ne__(self, other):
        result = self.__eq__(other)
        return not result

    def __lt__(self, other):
        if not isinstance(other, Money):
            raise MoneyComparisonError(other)
        if (self.currency == other.currency):
            return (self.amount < other.amount)
        else:
            raise TypeError('Cannot compare Money with different currencies.')

    def __gt__(self, other):
        if not isinstance(other, Money):
            raise MoneyComparisonError(other)
        if (self.currency == other.currency):
            return (self.amount > other.amount)
        else:
            raise TypeError('Cannot compare Money with different currencies.')

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other


# ____________________________________________________________________
# Definitions of ISO 4217 Currencies
# Source: http://www.iso.org/iso/support/faqs/faqs_widely_used_standards/widely_used_standards_other/currency_codes/currency_codes_list-1.htm

CURRENCIES = {}


def add_currency(code, numeric, name, countries):
    global CURRENCIES
    CURRENCIES[code] = Currency(
        code=code,
        numeric=numeric,
        name=name,
        countries=countries)
    return CURRENCIES[code]


def get_currency(code):
    try:
        return CURRENCIES[code]
    except KeyError:
        raise CurrencyDoesNotExist(code)

DEFAULT_CURRENCY = add_currency(DEFAULT_CURRENCY_CODE, '999', 'Default currency.', [])


AED = add_currency('AED', '784', 'UAE Dirham', ['UNITED ARAB EMIRATES'])
AFN = add_currency('AFN', '971', 'Afghani', ['AFGHANISTAN'])
ALL = add_currency('ALL', '008', 'Lek', ['ALBANIA'])
AMD = add_currency('AMD', '051', 'Armenian Dram', ['ARMENIA'])
ANG = add_currency('ANG', '532', 'Netherlands Antillian Guilder', ['NETHERLANDS ANTILLES'])
AOA = add_currency('AOA', '973', 'Kwanza', ['ANGOLA'])
ARS = add_currency('ARS', '032', 'Argentine Peso', ['ARGENTINA'])
AUD = add_currency('AUD', '036', 'Australian Dollar', ['AUSTRALIA', 'CHRISTMAS ISLAND', 'COCOS (KEELING) ISLANDS', 'HEARD ISLAND AND MCDONALD ISLANDS', 'KIRIBATI', 'NAURU', 'NORFOLK ISLAND', 'TUVALU'])
AWG = add_currency('AWG', '533', 'Aruban Guilder', ['ARUBA'])
AZN = add_currency('AZN', '944', 'Azerbaijanian Manat', ['AZERBAIJAN'])
BAM = add_currency('BAM', '977', 'Convertible Marks', ['BOSNIA AND HERZEGOVINA'])
BBD = add_currency('BBD', '052', 'Barbados Dollar', ['BARBADOS'])
BDT = add_currency('BDT', '050', 'Taka', ['BANGLADESH'])
BGN = add_currency('BGN', '975', 'Bulgarian Lev', ['BULGARIA'])
BHD = add_currency('BHD', '048', 'Bahraini Dinar', ['BAHRAIN'])
BIF = add_currency('BIF', '108', 'Burundi Franc', ['BURUNDI'])
BMD = add_currency('BMD', '060', 'Bermudian Dollar (customarily known as Bermuda Dollar)', ['BERMUDA'])
BND = add_currency('BND', '096', 'Brunei Dollar', ['BRUNEI DARUSSALAM'])
BRL = add_currency('BRL', '986', 'Brazilian Real', ['BRAZIL'])
BSD = add_currency('BSD', '044', 'Bahamian Dollar', ['BAHAMAS'])
BTN = add_currency('BTN', '064', 'Bhutanese ngultrum', ['BHUTAN'])
BWP = add_currency('BWP', '072', 'Pula', ['BOTSWANA'])
BYR = add_currency('BYR', '974', 'Belarussian Ruble', ['BELARUS'])
BZD = add_currency('BZD', '084', 'Belize Dollar', ['BELIZE'])
CAD = add_currency('CAD', '124', 'Canadian Dollar', ['CANADA'])
CDF = add_currency('CDF', '976', 'Congolese franc', ['DEMOCRATIC REPUBLIC OF CONGO'])
CHF = add_currency('CHF', '756', 'Swiss Franc', ['LIECHTENSTEIN'])
CLP = add_currency('CLP', '152', 'Chilean peso', ['CHILE'])
CNY = add_currency('CNY', '156', 'Yuan Renminbi', ['CHINA'])
COP = add_currency('COP', '170', 'Colombian peso', ['COLOMBIA'])
CRC = add_currency('CRC', '188', 'Costa Rican Colon', ['COSTA RICA'])
CUC = add_currency('CUC', '931', 'Cuban convertible peso', ['CUBA'])
CUP = add_currency('CUP', '192', 'Cuban Peso', ['CUBA'])
CVE = add_currency('CVE', '132', 'Cape Verde Escudo', ['CAPE VERDE'])
CZK = add_currency('CZK', '203', 'Czech Koruna', ['CZECH REPUBLIC'])
DJF = add_currency('DJF', '262', 'Djibouti Franc', ['DJIBOUTI'])
DKK = add_currency('DKK', '208', 'Danish Krone', ['DENMARK', 'FAROE ISLANDS', 'GREENLAND'])
DOP = add_currency('DOP', '214', 'Dominican Peso', ['DOMINICAN REPUBLIC'])
DZD = add_currency('DZD', '012', 'Algerian Dinar', ['ALGERIA'])
EEK = add_currency('EEK', '233', 'Kroon', ['ESTONIA'])
EGP = add_currency('EGP', '818', 'Egyptian Pound', ['EGYPT'])
ERN = add_currency('ERN', '232', 'Nakfa', ['ERITREA'])
ETB = add_currency('ETB', '230', 'Ethiopian Birr', ['ETHIOPIA'])
EUR = add_currency('EUR', '978', 'Euro', ['ANDORRA', 'AUSTRIA', 'BELGIUM', 'FINLAND', 'FRANCE', 'FRENCH GUIANA', 'FRENCH SOUTHERN TERRITORIES', 'GERMANY', 'GREECE', 'GUADELOUPE', 'IRELAND', 'ITALY', 'LUXEMBOURG', 'MARTINIQUE', 'MAYOTTE', 'MONACO', 'MONTENEGRO', 'NETHERLANDS', 'PORTUGAL', 'R.UNION', 'SAINT PIERRE AND MIQUELON', 'SAN MARINO', 'SLOVENIA', 'SPAIN'])
FJD = add_currency('FJD', '242', 'Fiji Dollar', ['FIJI'])
FKP = add_currency('FKP', '238', 'Falkland Islands Pound', ['FALKLAND ISLANDS (MALVINAS)'])
GBP = add_currency('GBP', '826', 'Pound Sterling', ['UNITED KINGDOM'])
GEL = add_currency('GEL', '981', 'Lari', ['GEORGIA'])
GHS = add_currency('GHS', '936', 'Ghana Cedi', ['GHANA'])
GIP = add_currency('GIP', '292', 'Gibraltar Pound', ['GIBRALTAR'])
GMD = add_currency('GMD', '270', 'Dalasi', ['GAMBIA'])
GNF = add_currency('GNF', '324', 'Guinea Franc', ['GUINEA'])
GTQ = add_currency('GTQ', '320', 'Quetzal', ['GUATEMALA'])
GYD = add_currency('GYD', '328', 'Guyana Dollar', ['GUYANA'])
HKD = add_currency('HKD', '344', 'Hong Kong Dollar', ['HONG KONG'])
HNL = add_currency('HNL', '340', 'Lempira', ['HONDURAS'])
HRK = add_currency('HRK', '191', 'Croatian Kuna', ['CROATIA'])
HTG = add_currency('HTG', '332', 'Haitian gourde', ['HAITI'])
HUF = add_currency('HUF', '348', 'Forint', ['HUNGARY'])
IDR = add_currency('IDR', '360', 'Rupiah', ['INDONESIA'])
ILS = add_currency('ILS', '376', 'New Israeli Sheqel', ['ISRAEL'])
IMP = add_currency('IMP', 'Nil', 'Isle of Man pount', ['ISLE OF MAN'])
INR = add_currency('INR', '356', 'Indian Rupee', ['INDIA'])
IQD = add_currency('IQD', '368', 'Iraqi Dinar', ['IRAQ'])
IRR = add_currency('IRR', '364', 'Iranian Rial', ['IRAN'])
ISK = add_currency('ISK', '352', 'Iceland Krona', ['ICELAND'])
JMD = add_currency('JMD', '388', 'Jamaican Dollar', ['JAMAICA'])
JOD = add_currency('JOD', '400', 'Jordanian Dinar', ['JORDAN'])
JPY = add_currency('JPY', '392', 'Yen', ['JAPAN'])
KES = add_currency('KES', '404', 'Kenyan Shilling', ['KENYA'])
KGS = add_currency('KGS', '417', 'Som', ['KYRGYZSTAN'])
KHR = add_currency('KHR', '116', 'Riel', ['CAMBODIA'])
KMF = add_currency('KMF', '174', 'Comoro Franc', ['COMOROS'])
KPW = add_currency('KPW', '408', 'North Korean Won', ['KOREA'])
KRW = add_currency('KRW', '410', 'Won', ['KOREA'])
KWD = add_currency('KWD', '414', 'Kuwaiti Dinar', ['KUWAIT'])
KYD = add_currency('KYD', '136', 'Cayman Islands Dollar', ['CAYMAN ISLANDS'])
KZT = add_currency('KZT', '398', 'Tenge', ['KAZAKHSTAN'])
LAK = add_currency('LAK', '418', 'Kip', ['LAO PEOPLES DEMOCRATIC REPUBLIC'])
LBP = add_currency('LBP', '422', 'Lebanese Pound', ['LEBANON'])
LKR = add_currency('LKR', '144', 'Sri Lanka Rupee', ['SRI LANKA'])
LRD = add_currency('LRD', '430', 'Liberian Dollar', ['LIBERIA'])
LSL = add_currency('LSL', '426', 'Lesotho loti', ['LESOTHO'])
LTL = add_currency('LTL', '440', 'Lithuanian Litas', ['LITHUANIA'])
LVL = add_currency('LVL', '428', 'Latvian Lats', ['LATVIA'])
LYD = add_currency('LYD', '434', 'Libyan Dinar', ['LIBYAN ARAB JAMAHIRIYA'])
MAD = add_currency('MAD', '504', 'Moroccan Dirham', ['MOROCCO', 'WESTERN SAHARA'])
MDL = add_currency('MDL', '498', 'Moldovan Leu', ['MOLDOVA'])
MGA = add_currency('MGA', '969', 'Malagasy Ariary', ['MADAGASCAR'])
MKD = add_currency('MKD', '807', 'Denar', ['MACEDONIA'])
MMK = add_currency('MMK', '104', 'Kyat', ['MYANMAR'])
MNT = add_currency('MNT', '496', 'Tugrik', ['MONGOLIA'])
MOP = add_currency('MOP', '446', 'Pataca', ['MACAO'])
MRO = add_currency('MRO', '478', 'Ouguiya', ['MAURITANIA'])
MUR = add_currency('MUR', '480', 'Mauritius Rupee', ['MAURITIUS'])
MVR = add_currency('MVR', '462', 'Rufiyaa', ['MALDIVES'])
MWK = add_currency('MWK', '454', 'Kwacha', ['MALAWI'])
MXN = add_currency('MXN', '484', 'Mexixan peso', ['MEXICO'])
MYR = add_currency('MYR', '458', 'Malaysian Ringgit', ['MALAYSIA'])
MZN = add_currency('MZN', '943', 'Metical', ['MOZAMBIQUE'])
NAD = add_currency('NAD', '516', 'Namibian Dollar', ['NAMIBIA'])
NGN = add_currency('NGN', '566', 'Naira', ['NIGERIA'])
NIO = add_currency('NIO', '558', 'Cordoba Oro', ['NICARAGUA'])
NOK = add_currency('NOK', '578', 'Norwegian Krone', ['BOUVET ISLAND', 'NORWAY', 'SVALBARD AND JAN MAYEN'])
NPR = add_currency('NPR', '524', 'Nepalese Rupee', ['NEPAL'])
NZD = add_currency('NZD', '554', 'New Zealand Dollar', ['COOK ISLANDS', ', prefix=None, suffix=NoneNEW ZEALAND', 'NIUE', 'PITCAIRN', 'TOKELAU'])
OMR = add_currency('OMR', '512', 'Rial Omani', ['OMAN'])
PEN = add_currency('PEN', '604', 'Nuevo Sol', ['PERU'])
PGK = add_currency('PGK', '598', 'Kina', ['PAPUA NEW GUINEA'])
PHP = add_currency('PHP', '608', 'Philippine Peso', ['PHILIPPINES'])
PKR = add_currency('PKR', '586', 'Pakistan Rupee', ['PAKISTAN'])
PLN = add_currency('PLN', '985', 'Zloty', ['POLAND'])
PYG = add_currency('PYG', '600', 'Guarani', ['PARAGUAY'])
QAR = add_currency('QAR', '634', 'Qatari Rial', ['QATAR'])
RON = add_currency('RON', '946', 'New Leu', ['ROMANIA'])
RSD = add_currency('RSD', '941', 'Serbian Dinar', ['SERBIA'])
RUB = add_currency('RUB', '643', 'Russian Ruble', ['RUSSIAN FEDERATION'])
RWF = add_currency('RWF', '646', 'Rwanda Franc', ['RWANDA'])
SAR = add_currency('SAR', '682', 'Saudi Riyal', ['SAUDI ARABIA'])
SBD = add_currency('SBD', '090', 'Solomon Islands Dollar', ['SOLOMON ISLANDS'])
SCR = add_currency('SCR', '690', 'Seychelles Rupee', ['SEYCHELLES'])
SDG = add_currency('SDG', '938', 'Sudanese Pound', ['SUDAN'])
SEK = add_currency('SEK', '752', 'Swedish Krona', ['SWEDEN'])
SGD = add_currency('SGD', '702', 'Singapore Dollar', ['SINGAPORE'])
SHP = add_currency('SHP', '654', 'Saint Helena Pound', ['SAINT HELENA'])
SKK = add_currency('SKK', '703', 'Slovak Koruna', ['SLOVAKIA'])
SLL = add_currency('SLL', '694', 'Leone', ['SIERRA LEONE'])
SOS = add_currency('SOS', '706', 'Somali Shilling', ['SOMALIA'])
SRD = add_currency('SRD', '968', 'Surinam Dollar', ['SURINAME'])
STD = add_currency('STD', '678', 'Dobra', ['SAO TOME AND PRINCIPE'])
SYP = add_currency('SYP', '760', 'Syrian Pound', ['SYRIAN ARAB REPUBLIC'])
SZL = add_currency('SZL', '748', 'Lilangeni', ['SWAZILAND'])
THB = add_currency('THB', '764', 'Baht', ['THAILAND'])
TJS = add_currency('TJS', '972', 'Somoni', ['TAJIKISTAN'])
TMM = add_currency('TMM', '795', 'Manat', ['TURKMENISTAN'])
TND = add_currency('TND', '788', 'Tunisian Dinar', ['TUNISIA'])
TOP = add_currency('TOP', '776', 'Paanga', ['TONGA'])
TRY = add_currency('TRY', '949', 'Turkish Lira', ['TURKEY'])
TTD = add_currency('TTD', '780', 'Trinidad and Tobago Dollar', ['TRINIDAD AND TOBAGO'])
TVD = add_currency('TVD', 'Nil', 'Tuvalu dollar', ['TUVALU'])
TWD = add_currency('TWD', '901', 'New Taiwan Dollar', ['TAIWAN'])
TZS = add_currency('TZS', '834', 'Tanzanian Shilling', ['TANZANIA'])
UAH = add_currency('UAH', '980', 'Hryvnia', ['UKRAINE'])
UGX = add_currency('UGX', '800', 'Uganda Shilling', ['UGANDA'])
USD = add_currency('USD', '840', 'US Dollar', ['AMERICAN SAMOA', 'BRITISH INDIAN OCEAN TERRITORY', 'ECUADOR', 'GUAM', 'MARSHALL ISLANDS', 'MICRONESIA', 'NORTHERN MARIANA ISLANDS', 'PALAU', 'PUERTO RICO', 'TIMOR-LESTE', 'TURKS AND CAICOS ISLANDS', 'UNITED STATES', 'UNITED STATES MINOR OUTLYING ISLANDS', 'VIRGIN ISLANDS (BRITISH)', 'VIRGIN ISLANDS (U.S.)'])
UYU = add_currency('UYU', '858', 'Uruguayan peso', ['URUGUAY'])
UZS = add_currency('UZS', '860', 'Uzbekistan Sum', ['UZBEKISTAN'])
VEF = add_currency('VEF', '937', 'Bolivar Fuerte', ['VENEZUELA'])
VND = add_currency('VND', '704', 'Dong', ['VIET NAM'])
VUV = add_currency('VUV', '548', 'Vatu', ['VANUATU'])
WST = add_currency('WST', '882', 'Tala', ['SAMOA'])
XAF = add_currency('XAF', '950', 'CFA franc BEAC', ['CAMEROON', 'CENTRAL AFRICAN REPUBLIC', 'REPUBLIC OF THE CONGO', 'CHAD', 'EQUATORIAL GUINEA', 'GABON'])
XAG = add_currency('XAG', '961', 'Silver', [])
XAU = add_currency('XAU', '959', 'Gold', [])
XBA = add_currency('XBA', '955', 'Bond Markets Units European Composite Unit (EURCO)', [])
XBB = add_currency('XBB', '956', 'European Monetary Unit (E.M.U.-6)', [])
XBC = add_currency('XBC', '957', 'European Unit of Account 9(E.U.A.-9)', [])
XBD = add_currency('XBD', '958', 'European Unit of Account 17(E.U.A.-17)', [])
XCD = add_currency('XCD', '951', 'East Caribbean Dollar', ['ANGUILLA', 'ANTIGUA AND BARBUDA', 'DOMINICA', 'GRENADA', 'MONTSERRAT', 'SAINT KITTS AND NEVIS', 'SAINT LUCIA', 'SAINT VINCENT AND THE GRENADINES'])
XDR = add_currency('XDR', '960', 'SDR', ['INTERNATIONAL MONETARY FUND (I.M.F)'])
XFO = add_currency('XFO', 'Nil', 'Gold-Franc', [])
XFU = add_currency('XFU', 'Nil', 'UIC-Franc', [])
XOF = add_currency('XOF', '952', 'CFA Franc BCEAO', ['BENIN', 'BURKINA FASO', 'COTE D\'IVOIRE', 'GUINEA-BISSAU', 'MALI', 'NIGER', 'SENEGAL', 'TOGO'])
XPD = add_currency('XPD', '964', 'Palladium', [])
XPF = add_currency('XPF', '953', 'CFP Franc', ['FRENCH POLYNESIA', 'NEW CALEDONIA', 'WALLIS AND FUTUNA'])
XPT = add_currency('XPT', '962', 'Platinum', [])
XTS = add_currency('XTS', '963', 'Codes specifically reserved for testing purposes', [])
YER = add_currency('YER', '886', 'Yemeni Rial', ['YEMEN'])
ZAR = add_currency('ZAR', '710', 'Rand', ['SOUTH AFRICA'])
ZMK = add_currency('ZMK', '894', 'Kwacha', ['ZAMBIA'])
ZWD = add_currency('ZWD', '716', 'Zimbabwe Dollar A/06', ['ZIMBABWE'])
ZWL = add_currency('ZWL', '932', 'Zimbabwe dollar A/09', ['ZIMBABWE'])
ZWN = add_currency('ZWN', '942', 'Zimbabwe dollar A/08', ['ZIMBABWE'])

########NEW FILE########
__FILENAME__ = localization
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from decimal import Decimal, ROUND_HALF_EVEN
import moneyed

DEFAULT = "default"


class CurrencyFormatter(object):

    sign_definitions = {}
    formatting_definitions = {}

    def add_sign_definition(self, locale, currency, prefix='', suffix=''):
        locale = locale.upper()
        currency_code = currency.code.upper()
        if not locale in self.sign_definitions:
            self.sign_definitions[locale] = {}
        self.sign_definitions[locale][currency_code] = (prefix, suffix)

    def add_formatting_definition(self, locale, group_size,
                                  group_separator, decimal_point,
                                  positive_sign, trailing_positive_sign,
                                  negative_sign, trailing_negative_sign,
                                  rounding_method):
        locale = locale.upper()
        self.formatting_definitions[locale] = {
            'group_size': group_size,
            'group_separator': group_separator,
            'decimal_point': decimal_point,
            'positive_sign': positive_sign,
            'trailing_positive_sign': trailing_positive_sign,
            'negative_sign': negative_sign,
            'trailing_negative_sign': trailing_negative_sign,
            'rounding_method': rounding_method}

    def get_sign_definition(self, currency_code, locale):
        currency_code = currency_code.upper()

        if locale.upper() not in self.sign_definitions:
            locale = DEFAULT

        local_set = self.sign_definitions.get(locale.upper())

        if currency_code in local_set:
            return local_set.get(currency_code)
        else:
            return ('', " %s" % currency_code)

    def get_formatting_definition(self, locale):
        locale = locale.upper()
        if locale in self.formatting_definitions:
            return self.formatting_definitions.get(locale)
        else:
            return self.formatting_definitions.get(DEFAULT)

    def format(self, money, include_symbol=True, locale=DEFAULT,
               decimal_places=None, rounding_method=None):
        locale = locale.upper()
        code = money.currency.code.upper()
        prefix, suffix = self.get_sign_definition(code, locale)
        formatting = self.get_formatting_definition(locale)

        if rounding_method is None:
            rounding_method = formatting['rounding_method']

        if decimal_places is None:
            # TODO: Use individual defaults for each currency
            decimal_places = 2

        q = Decimal(10) ** -decimal_places  # 2 places --> '0.01'
        quantized = money.amount.quantize(q, rounding_method)
        negative, digits, e = quantized.as_tuple()

        result = []

        digits = list(map(str, digits))

        build, next = result.append, digits.pop

        # Trailing sign
        if negative:
            build(formatting['trailing_negative_sign'])
        else:
            build(formatting['trailing_positive_sign'])

        # Suffix
        if include_symbol:
            build(suffix)

        # Decimals
        for i in range(decimal_places):
            build(next() if digits else '0')

        # Decimal points
        if decimal_places:
            build(formatting['decimal_point'])

        # Grouped number
        if not digits:
            build('0')
        else:
            i = 0
            while digits:
                build(next())
                i += 1
                if i == formatting['group_size'] and digits:
                    i = 0
                    build(formatting['group_separator'])

        # Prefix
        if include_symbol:
            build(prefix)

        # Sign
        if negative:
            build(formatting['negative_sign'])
        else:
            build(formatting['positive_sign'])

        return ''.join(reversed(result))

_FORMATTER = CurrencyFormatter()

format_money = _FORMATTER.format

_sign = _FORMATTER.add_sign_definition
_format = _FORMATTER.add_formatting_definition

## FORMATTING RULES

_format(DEFAULT, group_size=3, group_separator=",", decimal_point=".",
                 positive_sign="", trailing_positive_sign="",
                 negative_sign="-", trailing_negative_sign="",
                 rounding_method=ROUND_HALF_EVEN)

_format("en_US", group_size=3, group_separator=",", decimal_point=".",
                 positive_sign="", trailing_positive_sign="",
                 negative_sign="-", trailing_negative_sign="",
                 rounding_method=ROUND_HALF_EVEN)
                 
_format("de_DE", group_size=3, group_separator=" ", decimal_point=",",
                 positive_sign="", trailing_positive_sign="",
                 negative_sign="-", trailing_negative_sign="",
                 rounding_method=ROUND_HALF_EVEN)
                 
_format("de_AT", group_size=3, group_separator=" ", decimal_point=",",
                 positive_sign="", trailing_positive_sign="",
                 negative_sign="-", trailing_negative_sign="",
                 rounding_method=ROUND_HALF_EVEN)
                 
_format("de_CH", group_size=3, group_separator=" ", decimal_point=".",
                 positive_sign="", trailing_positive_sign="",
                 negative_sign="-", trailing_negative_sign="",
                 rounding_method=ROUND_HALF_EVEN)

_format("sv_SE", group_size=3, group_separator=" ", decimal_point=",",
                 positive_sign="", trailing_positive_sign="",
                 negative_sign="-", trailing_negative_sign="",
                 rounding_method=ROUND_HALF_EVEN)

_format("pl_PL", group_size=3, group_separator=" ", decimal_point=",",
                 positive_sign="", trailing_positive_sign="",
                 negative_sign="-", trailing_negative_sign="",
                 rounding_method=ROUND_HALF_EVEN)

## CURRENCY SIGNS
# Default currency signs. These can be overridden for locales where
# foreign or local currency signs for one reason or another differ
# from the norm.

# There may be errors here, they have been entered manually. Please
# fork and fix if you find errors.
# Code lives here (2011-05-08): https://github.com/limist/py-moneyed

_sign(DEFAULT, moneyed.AED, prefix='د.إ')
_sign(DEFAULT, moneyed.AFN, suffix='؋')
_sign(DEFAULT, moneyed.ALL, prefix='L')
_sign(DEFAULT, moneyed.AMD, prefix='Դ')
_sign(DEFAULT, moneyed.ANG, prefix='ƒ')
_sign(DEFAULT, moneyed.AOA, prefix='Kz')
_sign(DEFAULT, moneyed.ARS, prefix='ARS$')
_sign(DEFAULT, moneyed.AUD, prefix='A$')
_sign(DEFAULT, moneyed.AWG, prefix='ƒ')
_sign(DEFAULT, moneyed.BAM, prefix='КМ')
_sign(DEFAULT, moneyed.BBD, prefix='Bds$')
_sign(DEFAULT, moneyed.BDT, prefix='৳')
_sign(DEFAULT, moneyed.BGN, prefix='лв')
_sign(DEFAULT, moneyed.BHD, prefix='.د.ب')
_sign(DEFAULT, moneyed.BIF, prefix='FBu')
_sign(DEFAULT, moneyed.BMD, prefix='BD$')
_sign(DEFAULT, moneyed.BND, prefix='B$')
_sign(DEFAULT, moneyed.BRL, prefix='R$')
_sign(DEFAULT, moneyed.BSD, prefix='B$')
_sign(DEFAULT, moneyed.BTN, prefix='Nu.')
_sign(DEFAULT, moneyed.BWP, prefix='P')
_sign(DEFAULT, moneyed.BYR, prefix='Br')
_sign(DEFAULT, moneyed.BZD, prefix='BZ$')
_sign(DEFAULT, moneyed.CAD, prefix='C$')
_sign(DEFAULT, moneyed.CDF, prefix='C₣')
_sign(DEFAULT, moneyed.CHF, prefix='Fr.')
_sign(DEFAULT, moneyed.CLP, prefix='CLP$')
_sign(DEFAULT, moneyed.CNY, prefix='¥')
_sign(DEFAULT, moneyed.COP, prefix='COL$')
_sign(DEFAULT, moneyed.CRC, prefix='₡')
_sign(DEFAULT, moneyed.CUC, prefix='CUC$')
_sign(DEFAULT, moneyed.CUP, prefix='$MN')
_sign(DEFAULT, moneyed.CVE, prefix='Esc')
_sign(DEFAULT, moneyed.CZK, prefix='Kč')
_sign(DEFAULT, moneyed.DJF, prefix='D₣')
_sign(DEFAULT, moneyed.DKK, suffix=' Dkr')
_sign(DEFAULT, moneyed.DOP, prefix='RD$')
_sign(DEFAULT, moneyed.DZD, prefix='دج')
_sign(DEFAULT, moneyed.EGP, prefix='ج.م.')
_sign(DEFAULT, moneyed.ERN, prefix='Nfk')
_sign(DEFAULT, moneyed.ETB, prefix='Br')
_sign(DEFAULT, moneyed.EUR, suffix=' €')
_sign(DEFAULT, moneyed.FJD, prefix='FJ$')
_sign(DEFAULT, moneyed.FKP, prefix='FK£')
_sign(DEFAULT, moneyed.GBP, prefix='GB£')
_sign(DEFAULT, moneyed.GEL, prefix='ლ')
_sign(DEFAULT, moneyed.GHS, prefix='₵')
_sign(DEFAULT, moneyed.GIP, prefix='GIP£')
_sign(DEFAULT, moneyed.GMD, prefix='D')
_sign(DEFAULT, moneyed.GNF, prefix='G₣')
_sign(DEFAULT, moneyed.GTQ, prefix='Q')
_sign(DEFAULT, moneyed.GYD, prefix='G$')
_sign(DEFAULT, moneyed.HKD, prefix='HK$')
_sign(DEFAULT, moneyed.HNL, prefix='L')
_sign(DEFAULT, moneyed.HRK, suffix='kn')
_sign(DEFAULT, moneyed.HTG, prefix='G')
_sign(DEFAULT, moneyed.HUF, prefix='Ft')
_sign(DEFAULT, moneyed.IDR, prefix='Rp')
_sign(DEFAULT, moneyed.ILS, prefix='₪')
_sign(DEFAULT, moneyed.IMP, prefix='IM£')
_sign(DEFAULT, moneyed.INR, prefix='₹')
_sign(DEFAULT, moneyed.IQD, prefix='ع.د')
_sign(DEFAULT, moneyed.IRR, prefix='ریال')
_sign(DEFAULT, moneyed.ISK, suffix=' Íkr')
_sign(DEFAULT, moneyed.JMD, prefix='J$')
_sign(DEFAULT, moneyed.JOD, prefix='JD')
_sign(DEFAULT, moneyed.JPY, prefix='¥')
_sign(DEFAULT, moneyed.KES, prefix='Ksh')
_sign(DEFAULT, moneyed.KGS, prefix='лв')
_sign(DEFAULT, moneyed.KHR, prefix='៛')
_sign(DEFAULT, moneyed.KMF, prefix='C₣')
_sign(DEFAULT, moneyed.KPW, prefix='₩')
_sign(DEFAULT, moneyed.KRW, prefix='₩')
_sign(DEFAULT, moneyed.KWD, prefix='د.ك')
_sign(DEFAULT, moneyed.KYD, prefix='CI$')
_sign(DEFAULT, moneyed.LAK, prefix='₭')
_sign(DEFAULT, moneyed.LBP, prefix='LL')
_sign(DEFAULT, moneyed.LKR, prefix='₨')
_sign(DEFAULT, moneyed.LRD, prefix='LD$')
_sign(DEFAULT, moneyed.LSL, prefix='M')
_sign(DEFAULT, moneyed.LTL, prefix='Lt')
_sign(DEFAULT, moneyed.LVL, prefix='Ls')
_sign(DEFAULT, moneyed.LYD, prefix='ل.د')
_sign(DEFAULT, moneyed.MAD, prefix='د.م.')
_sign(DEFAULT, moneyed.MGA, prefix='Ar')
_sign(DEFAULT, moneyed.MKD, prefix='ден')
_sign(DEFAULT, moneyed.MMK, prefix='K')
_sign(DEFAULT, moneyed.MNT, prefix='₮')
_sign(DEFAULT, moneyed.MOP, prefix='MOP$')
_sign(DEFAULT, moneyed.MRO, prefix='UM')
_sign(DEFAULT, moneyed.MUR, prefix='₨')
_sign(DEFAULT, moneyed.MVR, prefix='Rf.')
_sign(DEFAULT, moneyed.MWK, prefix='MK')
_sign(DEFAULT, moneyed.MXN, prefix='Mex$')
_sign(DEFAULT, moneyed.MYR, prefix='RM')
_sign(DEFAULT, moneyed.MZN, prefix='MT')
_sign(DEFAULT, moneyed.NAD, prefix='N$')
_sign(DEFAULT, moneyed.NGN, prefix='₦')
_sign(DEFAULT, moneyed.NIO, prefix='C$')
_sign(DEFAULT, moneyed.NOK, suffix=' Nkr')
_sign(DEFAULT, moneyed.NPR, prefix='₨')
_sign(DEFAULT, moneyed.NZD, prefix='NZ$')
_sign(DEFAULT, moneyed.OMR, prefix='ر.ع.')
_sign(DEFAULT, moneyed.PEN, prefix='S/.')
_sign(DEFAULT, moneyed.PGK, prefix='K')
_sign(DEFAULT, moneyed.PHP, prefix='₱')
_sign(DEFAULT, moneyed.PKR, prefix='₨')
_sign(DEFAULT, moneyed.PLN, suffix=' zł')
_sign(DEFAULT, moneyed.PYG, prefix='₲')
_sign(DEFAULT, moneyed.QAR, prefix='ر.ق')
_sign(DEFAULT, moneyed.RSD, prefix='дин')
_sign(DEFAULT, moneyed.RUB, prefix='руб.')
_sign(DEFAULT, moneyed.RWF, prefix='FRw')
_sign(DEFAULT, moneyed.SAR, prefix='ر.س')
_sign(DEFAULT, moneyed.SBD, prefix='SI$')
_sign(DEFAULT, moneyed.SCR, prefix='SRe')
_sign(DEFAULT, moneyed.SDG, prefix='S£')
_sign(DEFAULT, moneyed.SEK, suffix=' Skr')
_sign(DEFAULT, moneyed.SGD, prefix='S$')
_sign(DEFAULT, moneyed.SHP, prefix='SH£')
_sign(DEFAULT, moneyed.SLL, prefix='Le')
_sign(DEFAULT, moneyed.SOS, prefix='Sh.So.')
_sign(DEFAULT, moneyed.SRD, prefix='SRD$')
_sign(DEFAULT, moneyed.STD, prefix='Db')
_sign(DEFAULT, moneyed.SYP, prefix='£S')
_sign(DEFAULT, moneyed.SZL, prefix='E')
_sign(DEFAULT, moneyed.THB, prefix='฿')
_sign(DEFAULT, moneyed.TND, prefix='د.ت')
_sign(DEFAULT, moneyed.TOP, prefix='TOP$')
_sign(DEFAULT, moneyed.TRY, prefix='TL')
_sign(DEFAULT, moneyed.TTD, prefix='TT$')
_sign(DEFAULT, moneyed.TVD, prefix='$T')
_sign(DEFAULT, moneyed.TWD, prefix='NT$')
_sign(DEFAULT, moneyed.UAH, prefix='₴')
_sign(DEFAULT, moneyed.UGX, prefix='USh')
_sign(DEFAULT, moneyed.USD, prefix='US$')
_sign(DEFAULT, moneyed.UYU, prefix='$U')
_sign(DEFAULT, moneyed.VEF, prefix='Bs.')
_sign(DEFAULT, moneyed.VND, prefix='₫')
_sign(DEFAULT, moneyed.VUV, prefix='VT')
_sign(DEFAULT, moneyed.WST, prefix='WS$')
_sign(DEFAULT, moneyed.XAF, prefix='FCFA')
_sign(DEFAULT, moneyed.XCD, prefix='EC$')
_sign(DEFAULT, moneyed.XDR, prefix='SDR')
_sign(DEFAULT, moneyed.XOF, prefix='CFA')
_sign(DEFAULT, moneyed.ZAR, prefix='R')
_sign(DEFAULT, moneyed.ZMK, prefix='ZK')
_sign(DEFAULT, moneyed.ZWL, prefix='Z$')

_sign('en_US', moneyed.USD, prefix='$')
_sign('en_UK', moneyed.GBP, prefix='£')
_sign('sv_SE', moneyed.SEK, prefix=' kr')
_sign('pl_PL', moneyed.PLN, suffix=' zł')
_sign('de_DE', moneyed.EUR, suffix=' €')
_sign('de_AT', moneyed.EUR, suffix=' €')
_sign('de_CH', moneyed.CHF, prefix='Fr.')

########NEW FILE########
__FILENAME__ = test_moneyed_classes
# -*- encoding: utf-8 -*-
#file test_moneyed_classes.py
from __future__ import division
from __future__ import unicode_literals
from decimal import Decimal
import pytest  # Works with less code, more consistency than unittest.

from moneyed.classes import Currency, Money, MoneyComparisonError, CURRENCIES, DEFAULT_CURRENCY
from moneyed.localization import format_money


class TestCurrency:

    def setup_method(self, method):
        self.default_curr_code = 'XYZ'
        self.default_curr = CURRENCIES[self.default_curr_code]

    def test_init(self):
        usd_countries = CURRENCIES['USD'].countries
        US_dollars = Currency(
            code='USD',
            numeric='840',
            name='US Dollar',
            countries=['AMERICAN SAMOA',
                       'BRITISH INDIAN OCEAN TERRITORY',
                       'ECUADOR',
                       'GUAM',
                       'MARSHALL ISLANDS',
                       'MICRONESIA',
                       'NORTHERN MARIANA ISLANDS',
                       'PALAU',
                       'PUERTO RICO',
                       'TIMOR-LESTE',
                       'TURKS AND CAICOS ISLANDS',
                       'UNITED STATES',
                       'UNITED STATES MINOR OUTLYING ISLANDS',
                       'VIRGIN ISLANDS (BRITISH)',
                       'VIRGIN ISLANDS (U.S.)'])
        assert US_dollars.code == 'USD'
        assert US_dollars.countries == usd_countries
        assert US_dollars.name == 'US Dollar'
        assert US_dollars.numeric == '840'

    def test_repr(self):
        assert str(self.default_curr) == self.default_curr_code


class TestMoney:

    def setup_method(self, method):
        self.one_million_decimal = Decimal('1000000')
        self.USD = CURRENCIES['USD']
        self.one_million_bucks = Money(amount=self.one_million_decimal,
                                       currency=self.USD)

    def test_init(self):
        one_million_dollars = Money(amount=self.one_million_decimal,
                                    currency=self.USD)
        assert one_million_dollars.amount == self.one_million_decimal
        assert one_million_dollars.currency == self.USD

    def test_init_string_currency_code(self):
        one_million_dollars = Money(amount=self.one_million_decimal,
                                    currency='usd')
        assert one_million_dollars.amount == self.one_million_decimal
        assert one_million_dollars.currency == self.USD

    def test_init_default_currency(self):
        one_million = self.one_million_decimal
        one_million_dollars = Money(amount=one_million)  # No currency given!
        assert one_million_dollars.amount == one_million
        assert one_million_dollars.currency == DEFAULT_CURRENCY

    def test_init_float(self):
        one_million_dollars = Money(amount=1000000.0)
        assert one_million_dollars.amount == self.one_million_decimal

    def test_repr(self):
        assert repr(self.one_million_bucks) == '1000000 USD'
        assert repr(Money(Decimal('2.000'), 'PLN')) == '2 PLN'
        m_1 = Money(Decimal('2.000'), 'PLN')
        m_2 = Money(Decimal('2.000000'), 'PLN')
        assert repr(m_1) == repr(m_2)

    def test_str(self):
        assert str(self.one_million_bucks) == 'US$1,000,000.00'

    def test_format_money(self):
        # Two decimal places by default
        assert format_money(self.one_million_bucks) == 'US$1,000,000.00'
        # No decimal point without fractional part
        assert format_money(self.one_million_bucks, decimal_places=0) == 'US$1,000,000'
        # locale == pl_PL
        one_million_pln = Money('1000000', 'PLN')
        # Two decimal places by default
        assert format_money(one_million_pln, locale='pl_PL') == '1 000 000,00 zł'
        assert format_money(self.one_million_bucks, locale='pl_PL') == '1 000 000,00 USD'
        # No decimal point without fractional part
        assert format_money(one_million_pln, locale='pl_PL',
                            decimal_places=0) == '1 000 000 zł'

    def test_add(self):
        assert (self.one_million_bucks + self.one_million_bucks
                == Money(amount='2000000', currency=self.USD))

    def test_add_non_money(self):
        with pytest.raises(TypeError):
            Money(1000) + 123

    def test_sub(self):
        zeroed_test = self.one_million_bucks - self.one_million_bucks
        assert zeroed_test == Money(amount=0, currency=self.USD)

    def test_sub_non_money(self):
        with pytest.raises(TypeError):
            Money(1000) - 123

    def test_mul(self):
        x = Money(amount=111.33, currency=self.USD)
        assert 3 * x == Money(333.99, currency=self.USD)
        assert Money(333.99, currency=self.USD) == 3 * x

    def test_mul_bad(self):
        with pytest.raises(TypeError):
            self.one_million_bucks * self.one_million_bucks

    def test_div(self):
        x = Money(amount=50, currency=self.USD)
        y = Money(amount=2, currency=self.USD)
        assert x / y == Decimal(25)

    def test_div_mismatched_currencies(self):
        x = Money(amount=50, currency=self.USD)
        y = Money(amount=2, currency=CURRENCIES['CAD'])
        with pytest.raises(TypeError):
            assert x / y == Money(amount=25, currency=self.USD)

    def test_div_by_non_Money(self):
        x = Money(amount=50, currency=self.USD)
        y = 2
        assert x / y == Money(amount=25, currency=self.USD)

    def test_rmod(self):
        assert 1 % self.one_million_bucks == Money(amount=10000,
                                                   currency=self.USD)

    def test_rmod_bad(self):
        with pytest.raises(TypeError):
            assert (self.one_million_bucks % self.one_million_bucks
                    == 1)

    def test_convert_to_default(self):
        # Currency conversions are not implemented as of 2/2011; when
        # they are working, then convert_to_default and convert_to
        # will need to be tested.
        pass

    # Note: no tests for __eq__ as it's quite thoroughly covered in
    # the assert comparisons throughout these tests.

    def test_ne(self):
        x = Money(amount=1, currency=self.USD)
        assert self.one_million_bucks != x

    def test_equality_to_other_types(self):
        x = Money(amount=1, currency=self.USD)
        assert self.one_million_bucks != None
        assert self.one_million_bucks != {}

    def test_not_equal_to_decimal_types(self):
        assert self.one_million_bucks != self.one_million_decimal

    def test_lt(self):
        x = Money(amount=1, currency=self.USD)
        assert x < self.one_million_bucks

    def test_lt_mistyped(self):
        x = 1.0
        with pytest.raises(MoneyComparisonError):
            assert x < self.one_million_bucks

    def test_gt(self):
        x = Money(amount=1, currency=self.USD)
        assert self.one_million_bucks > x

    def test_gt_mistyped(self):
        x = 1.0
        with pytest.raises(MoneyComparisonError):
            assert self.one_million_bucks > x

    def test_abs(self):
        abs_money = Money(amount=1, currency=self.USD)
        x = Money(amount=-1, currency=self.USD)
        assert abs(x) == abs_money
        y = Money(amount=1, currency=self.USD)
        assert abs(x) == abs_money

########NEW FILE########
