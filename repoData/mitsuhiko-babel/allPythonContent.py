__FILENAME__ = core
# -*- coding: utf-8 -*-
"""
    babel.core
    ~~~~~~~~~~

    Core locale representation and locale data access.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import os

from babel import localedata
from babel._compat import pickle, string_types
from babel.plural import PluralRule

__all__ = ['UnknownLocaleError', 'Locale', 'default_locale', 'negotiate_locale',
           'parse_locale']


_global_data = None
_default_plural_rule = PluralRule({})


def _raise_no_data_error():
    raise RuntimeError('The babel data files are not available. '
                       'This usually happens because you are using '
                       'a source checkout from Babel and you did '
                       'not build the data files.  Just make sure '
                       'to run "python setup.py import_cldr" before '
                       'installing the library.')


def get_global(key):
    """Return the dictionary for the given key in the global data.

    The global data is stored in the ``babel/global.dat`` file and contains
    information independent of individual locales.

    >>> get_global('zone_aliases')['UTC']
    u'Etc/GMT'
    >>> get_global('zone_territories')['Europe/Berlin']
    u'DE'

    .. versionadded:: 0.9

    :param key: the data key
    """
    global _global_data
    if _global_data is None:
        dirname = os.path.join(os.path.dirname(__file__))
        filename = os.path.join(dirname, 'global.dat')
        if not os.path.isfile(filename):
            _raise_no_data_error()
        fileobj = open(filename, 'rb')
        try:
            _global_data = pickle.load(fileobj)
        finally:
            fileobj.close()
    return _global_data.get(key, {})


LOCALE_ALIASES = {
    'ar': 'ar_SY', 'bg': 'bg_BG', 'bs': 'bs_BA', 'ca': 'ca_ES', 'cs': 'cs_CZ',
    'da': 'da_DK', 'de': 'de_DE', 'el': 'el_GR', 'en': 'en_US', 'es': 'es_ES',
    'et': 'et_EE', 'fa': 'fa_IR', 'fi': 'fi_FI', 'fr': 'fr_FR', 'gl': 'gl_ES',
    'he': 'he_IL', 'hu': 'hu_HU', 'id': 'id_ID', 'is': 'is_IS', 'it': 'it_IT',
    'ja': 'ja_JP', 'km': 'km_KH', 'ko': 'ko_KR', 'lt': 'lt_LT', 'lv': 'lv_LV',
    'mk': 'mk_MK', 'nl': 'nl_NL', 'nn': 'nn_NO', 'no': 'nb_NO', 'pl': 'pl_PL',
    'pt': 'pt_PT', 'ro': 'ro_RO', 'ru': 'ru_RU', 'sk': 'sk_SK', 'sl': 'sl_SI',
    'sv': 'sv_SE', 'th': 'th_TH', 'tr': 'tr_TR', 'uk': 'uk_UA'
}


class UnknownLocaleError(Exception):
    """Exception thrown when a locale is requested for which no locale data
    is available.
    """

    def __init__(self, identifier):
        """Create the exception.

        :param identifier: the identifier string of the unsupported locale
        """
        Exception.__init__(self, 'unknown locale %r' % identifier)

        #: The identifier of the locale that could not be found.
        self.identifier = identifier


class Locale(object):
    """Representation of a specific locale.

    >>> locale = Locale('en', 'US')
    >>> repr(locale)
    "Locale('en', territory='US')"
    >>> locale.display_name
    u'English (United States)'

    A `Locale` object can also be instantiated from a raw locale string:

    >>> locale = Locale.parse('en-US', sep='-')
    >>> repr(locale)
    "Locale('en', territory='US')"

    `Locale` objects provide access to a collection of locale data, such as
    territory and language names, number and date format patterns, and more:

    >>> locale.number_symbols['decimal']
    u'.'

    If a locale is requested for which no locale data is available, an
    `UnknownLocaleError` is raised:

    >>> Locale.parse('en_DE')
    Traceback (most recent call last):
        ...
    UnknownLocaleError: unknown locale 'en_DE'

    For more information see :rfc:`3066`.
    """

    def __init__(self, language, territory=None, script=None, variant=None):
        """Initialize the locale object from the given identifier components.

        >>> locale = Locale('en', 'US')
        >>> locale.language
        'en'
        >>> locale.territory
        'US'

        :param language: the language code
        :param territory: the territory (country or region) code
        :param script: the script code
        :param variant: the variant code
        :raise `UnknownLocaleError`: if no locale data is available for the
                                     requested locale
        """
        #: the language code
        self.language = language
        #: the territory (country or region) code
        self.territory = territory
        #: the script code
        self.script = script
        #: the variant code
        self.variant = variant
        self.__data = None

        identifier = str(self)
        if not localedata.exists(identifier):
            raise UnknownLocaleError(identifier)

    @classmethod
    def default(cls, category=None, aliases=LOCALE_ALIASES):
        """Return the system default locale for the specified category.

        >>> for name in ['LANGUAGE', 'LC_ALL', 'LC_CTYPE', 'LC_MESSAGES']:
        ...     os.environ[name] = ''
        >>> os.environ['LANG'] = 'fr_FR.UTF-8'
        >>> Locale.default('LC_MESSAGES')
        Locale('fr', territory='FR')

        The following fallbacks to the variable are always considered:

        - ``LANGUAGE``
        - ``LC_ALL``
        - ``LC_CTYPE``
        - ``LANG``

        :param category: one of the ``LC_XXX`` environment variable names
        :param aliases: a dictionary of aliases for locale identifiers
        """
        # XXX: use likely subtag expansion here instead of the
        # aliases dictionary.
        locale_string = default_locale(category, aliases=aliases)
        return cls.parse(locale_string)

    @classmethod
    def negotiate(cls, preferred, available, sep='_', aliases=LOCALE_ALIASES):
        """Find the best match between available and requested locale strings.

        >>> Locale.negotiate(['de_DE', 'en_US'], ['de_DE', 'de_AT'])
        Locale('de', territory='DE')
        >>> Locale.negotiate(['de_DE', 'en_US'], ['en', 'de'])
        Locale('de')
        >>> Locale.negotiate(['de_DE', 'de'], ['en_US'])

        You can specify the character used in the locale identifiers to separate
        the differnet components. This separator is applied to both lists. Also,
        case is ignored in the comparison:

        >>> Locale.negotiate(['de-DE', 'de'], ['en-us', 'de-de'], sep='-')
        Locale('de', territory='DE')

        :param preferred: the list of locale identifers preferred by the user
        :param available: the list of locale identifiers available
        :param aliases: a dictionary of aliases for locale identifiers
        """
        identifier = negotiate_locale(preferred, available, sep=sep,
                                      aliases=aliases)
        if identifier:
            return Locale.parse(identifier, sep=sep)

    @classmethod
    def parse(cls, identifier, sep='_', resolve_likely_subtags=True):
        """Create a `Locale` instance for the given locale identifier.

        >>> l = Locale.parse('de-DE', sep='-')
        >>> l.display_name
        u'Deutsch (Deutschland)'

        If the `identifier` parameter is not a string, but actually a `Locale`
        object, that object is returned:

        >>> Locale.parse(l)
        Locale('de', territory='DE')

        This also can perform resolving of likely subtags which it does
        by default.  This is for instance useful to figure out the most
        likely locale for a territory you can use ``'und'`` as the
        language tag:

        >>> Locale.parse('und_AT')
        Locale('de', territory='AT')

        :param identifier: the locale identifier string
        :param sep: optional component separator
        :param resolve_likely_subtags: if this is specified then a locale will
                                       have its likely subtag resolved if the
                                       locale otherwise does not exist.  For
                                       instance ``zh_TW`` by itself is not a
                                       locale that exists but Babel can
                                       automatically expand it to the full
                                       form of ``zh_hant_TW``.  Note that this
                                       expansion is only taking place if no
                                       locale exists otherwise.  For instance
                                       there is a locale ``en`` that can exist
                                       by itself.
        :raise `ValueError`: if the string does not appear to be a valid locale
                             identifier
        :raise `UnknownLocaleError`: if no locale data is available for the
                                     requested locale
        """
        if identifier is None:
            return None
        elif isinstance(identifier, Locale):
            return identifier
        elif not isinstance(identifier, string_types):
            raise TypeError('Unxpected value for identifier: %r' % (identifier,))

        parts = parse_locale(identifier, sep=sep)
        input_id = get_locale_identifier(parts)

        def _try_load(parts):
            try:
                return cls(*parts)
            except UnknownLocaleError:
                return None

        def _try_load_reducing(parts):
            # Success on first hit, return it.
            locale = _try_load(parts)
            if locale is not None:
                return locale

            # Now try without script and variant
            locale = _try_load(parts[:2])
            if locale is not None:
                return locale

        locale = _try_load(parts)
        if locale is not None:
            return locale
        if not resolve_likely_subtags:
            raise UnknownLocaleError(input_id)

        # From here onwards is some very bad likely subtag resolving.  This
        # whole logic is not entirely correct but good enough (tm) for the
        # time being.  This has been added so that zh_TW does not cause
        # errors for people when they upgrade.  Later we should properly
        # implement ICU like fuzzy locale objects and provide a way to
        # maximize and minimize locale tags.

        language, territory, script, variant = parts
        language = get_global('language_aliases').get(language, language)
        territory = get_global('territory_aliases').get(territory, (territory,))[0]
        script = get_global('script_aliases').get(script, script)
        variant = get_global('variant_aliases').get(variant, variant)

        if territory == 'ZZ':
            territory = None
        if script == 'Zzzz':
            script = None

        parts = language, territory, script, variant

        # First match: try the whole identifier
        new_id = get_locale_identifier(parts)
        likely_subtag = get_global('likely_subtags').get(new_id)
        if likely_subtag is not None:
            locale = _try_load_reducing(parse_locale(likely_subtag))
            if locale is not None:
                return locale

        # If we did not find anything so far, try again with a
        # simplified identifier that is just the language
        likely_subtag = get_global('likely_subtags').get(language)
        if likely_subtag is not None:
            language2, _, script2, variant2 = parse_locale(likely_subtag)
            locale = _try_load_reducing((language2, territory, script2, variant2))
            if locale is not None:
                return locale

        raise UnknownLocaleError(input_id)

    def __eq__(self, other):
        for key in ('language', 'territory', 'script', 'variant'):
            if not hasattr(other, key):
                return False
        return (self.language == other.language) and \
            (self.territory == other.territory) and \
            (self.script == other.script) and \
            (self.variant == other.variant)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        parameters = ['']
        for key in ('territory', 'script', 'variant'):
            value = getattr(self, key)
            if value is not None:
                parameters.append('%s=%r' % (key, value))
        parameter_string = '%r' % self.language + ', '.join(parameters)
        return 'Locale(%s)' % parameter_string

    def __str__(self):
        return get_locale_identifier((self.language, self.territory,
                                      self.script, self.variant))

    @property
    def _data(self):
        if self.__data is None:
            self.__data = localedata.LocaleDataDict(localedata.load(str(self)))
        return self.__data

    def get_display_name(self, locale=None):
        """Return the display name of the locale using the given locale.

        The display name will include the language, territory, script, and
        variant, if those are specified.

        >>> Locale('zh', 'CN', script='Hans').get_display_name('en')
        u'Chinese (Simplified, China)'

        :param locale: the locale to use
        """
        if locale is None:
            locale = self
        locale = Locale.parse(locale)
        retval = locale.languages.get(self.language)
        if self.territory or self.script or self.variant:
            details = []
            if self.script:
                details.append(locale.scripts.get(self.script))
            if self.territory:
                details.append(locale.territories.get(self.territory))
            if self.variant:
                details.append(locale.variants.get(self.variant))
            details = filter(None, details)
            if details:
                retval += ' (%s)' % u', '.join(details)
        return retval

    display_name = property(get_display_name, doc="""\
        The localized display name of the locale.

        >>> Locale('en').display_name
        u'English'
        >>> Locale('en', 'US').display_name
        u'English (United States)'
        >>> Locale('sv').display_name
        u'svenska'

        :type: `unicode`
        """)

    def get_language_name(self, locale=None):
        """Return the language of this locale in the given locale.

        >>> Locale('zh', 'CN', script='Hans').get_language_name('de')
        u'Chinesisch'

        .. versionadded:: 1.0

        :param locale: the locale to use
        """
        if locale is None:
            locale = self
        locale = Locale.parse(locale)
        return locale.languages.get(self.language)

    language_name = property(get_language_name, doc="""\
        The localized language name of the locale.

        >>> Locale('en', 'US').language_name
        u'English'
    """)

    def get_territory_name(self, locale=None):
        """Return the territory name in the given locale."""
        if locale is None:
            locale = self
        locale = Locale.parse(locale)
        return locale.territories.get(self.territory)

    territory_name = property(get_territory_name, doc="""\
        The localized territory name of the locale if available.

        >>> Locale('de', 'DE').territory_name
        u'Deutschland'
    """)

    def get_script_name(self, locale=None):
        """Return the script name in the given locale."""
        if locale is None:
            locale = self
        locale = Locale.parse(locale)
        return locale.scripts.get(self.script)

    script_name = property(get_script_name, doc="""\
        The localized script name of the locale if available.

        >>> Locale('ms', 'SG', script='Latn').script_name
        u'Latin'
    """)

    @property
    def english_name(self):
        """The english display name of the locale.

        >>> Locale('de').english_name
        u'German'
        >>> Locale('de', 'DE').english_name
        u'German (Germany)'

        :type: `unicode`"""
        return self.get_display_name(Locale('en'))

    #{ General Locale Display Names

    @property
    def languages(self):
        """Mapping of language codes to translated language names.

        >>> Locale('de', 'DE').languages['ja']
        u'Japanisch'

        See `ISO 639 <http://www.loc.gov/standards/iso639-2/>`_ for
        more information.
        """
        return self._data['languages']

    @property
    def scripts(self):
        """Mapping of script codes to translated script names.

        >>> Locale('en', 'US').scripts['Hira']
        u'Hiragana'

        See `ISO 15924 <http://www.evertype.com/standards/iso15924/>`_
        for more information.
        """
        return self._data['scripts']

    @property
    def territories(self):
        """Mapping of script codes to translated script names.

        >>> Locale('es', 'CO').territories['DE']
        u'Alemania'

        See `ISO 3166 <http://www.iso.org/iso/en/prods-services/iso3166ma/>`_
        for more information.
        """
        return self._data['territories']

    @property
    def variants(self):
        """Mapping of script codes to translated script names.

        >>> Locale('de', 'DE').variants['1901']
        u'Alte deutsche Rechtschreibung'
        """
        return self._data['variants']

    #{ Number Formatting

    @property
    def currencies(self):
        """Mapping of currency codes to translated currency names.  This
        only returns the generic form of the currency name, not the count
        specific one.  If an actual number is requested use the
        :func:`babel.numbers.get_currency_name` function.

        >>> Locale('en').currencies['COP']
        u'Colombian Peso'
        >>> Locale('de', 'DE').currencies['COP']
        u'Kolumbianischer Peso'
        """
        return self._data['currency_names']

    @property
    def currency_symbols(self):
        """Mapping of currency codes to symbols.

        >>> Locale('en', 'US').currency_symbols['USD']
        u'$'
        >>> Locale('es', 'CO').currency_symbols['USD']
        u'US$'
        """
        return self._data['currency_symbols']

    @property
    def number_symbols(self):
        """Symbols used in number formatting.

        >>> Locale('fr', 'FR').number_symbols['decimal']
        u','
        """
        return self._data['number_symbols']

    @property
    def decimal_formats(self):
        """Locale patterns for decimal number formatting.

        >>> Locale('en', 'US').decimal_formats[None]
        <NumberPattern u'#,##0.###'>
        """
        return self._data['decimal_formats']

    @property
    def currency_formats(self):
        """Locale patterns for currency number formatting.

        >>> print Locale('en', 'US').currency_formats[None]
        <NumberPattern u'\\xa4#,##0.00'>
        """
        return self._data['currency_formats']

    @property
    def percent_formats(self):
        """Locale patterns for percent number formatting.

        >>> Locale('en', 'US').percent_formats[None]
        <NumberPattern u'#,##0%'>
        """
        return self._data['percent_formats']

    @property
    def scientific_formats(self):
        """Locale patterns for scientific number formatting.

        >>> Locale('en', 'US').scientific_formats[None]
        <NumberPattern u'#E0'>
        """
        return self._data['scientific_formats']

    #{ Calendar Information and Date Formatting

    @property
    def periods(self):
        """Locale display names for day periods (AM/PM).

        >>> Locale('en', 'US').periods['am']
        u'AM'
        """
        return self._data['periods']

    @property
    def days(self):
        """Locale display names for weekdays.

        >>> Locale('de', 'DE').days['format']['wide'][3]
        u'Donnerstag'
        """
        return self._data['days']

    @property
    def months(self):
        """Locale display names for months.

        >>> Locale('de', 'DE').months['format']['wide'][10]
        u'Oktober'
        """
        return self._data['months']

    @property
    def quarters(self):
        """Locale display names for quarters.

        >>> Locale('de', 'DE').quarters['format']['wide'][1]
        u'1. Quartal'
        """
        return self._data['quarters']

    @property
    def eras(self):
        """Locale display names for eras.

        >>> Locale('en', 'US').eras['wide'][1]
        u'Anno Domini'
        >>> Locale('en', 'US').eras['abbreviated'][0]
        u'BC'
        """
        return self._data['eras']

    @property
    def time_zones(self):
        """Locale display names for time zones.

        >>> Locale('en', 'US').time_zones['Europe/London']['long']['daylight']
        u'British Summer Time'
        >>> Locale('en', 'US').time_zones['America/St_Johns']['city']
        u'St. John\u2019s'
        """
        return self._data['time_zones']

    @property
    def meta_zones(self):
        """Locale display names for meta time zones.

        Meta time zones are basically groups of different Olson time zones that
        have the same GMT offset and daylight savings time.

        >>> Locale('en', 'US').meta_zones['Europe_Central']['long']['daylight']
        u'Central European Summer Time'

        .. versionadded:: 0.9
        """
        return self._data['meta_zones']

    @property
    def zone_formats(self):
        """Patterns related to the formatting of time zones.

        >>> Locale('en', 'US').zone_formats['fallback']
        u'%(1)s (%(0)s)'
        >>> Locale('pt', 'BR').zone_formats['region']
        u'Hor\\xe1rio %s'

        .. versionadded:: 0.9
        """
        return self._data['zone_formats']

    @property
    def first_week_day(self):
        """The first day of a week, with 0 being Monday.

        >>> Locale('de', 'DE').first_week_day
        0
        >>> Locale('en', 'US').first_week_day
        6
        """
        return self._data['week_data']['first_day']

    @property
    def weekend_start(self):
        """The day the weekend starts, with 0 being Monday.

        >>> Locale('de', 'DE').weekend_start
        5
        """
        return self._data['week_data']['weekend_start']

    @property
    def weekend_end(self):
        """The day the weekend ends, with 0 being Monday.

        >>> Locale('de', 'DE').weekend_end
        6
        """
        return self._data['week_data']['weekend_end']

    @property
    def min_week_days(self):
        """The minimum number of days in a week so that the week is counted as
        the first week of a year or month.

        >>> Locale('de', 'DE').min_week_days
        4
        """
        return self._data['week_data']['min_days']

    @property
    def date_formats(self):
        """Locale patterns for date formatting.

        >>> Locale('en', 'US').date_formats['short']
        <DateTimePattern u'M/d/yy'>
        >>> Locale('fr', 'FR').date_formats['long']
        <DateTimePattern u'd MMMM y'>
        """
        return self._data['date_formats']

    @property
    def time_formats(self):
        """Locale patterns for time formatting.

        >>> Locale('en', 'US').time_formats['short']
        <DateTimePattern u'h:mm a'>
        >>> Locale('fr', 'FR').time_formats['long']
        <DateTimePattern u'HH:mm:ss z'>
        """
        return self._data['time_formats']

    @property
    def datetime_formats(self):
        """Locale patterns for datetime formatting.

        >>> Locale('en').datetime_formats['full']
        u"{1} 'at' {0}"
        >>> Locale('th').datetime_formats['medium']
        u'{1}, {0}'
        """
        return self._data['datetime_formats']

    @property
    def plural_form(self):
        """Plural rules for the locale.

        >>> Locale('en').plural_form(1)
        'one'
        >>> Locale('en').plural_form(0)
        'other'
        >>> Locale('fr').plural_form(0)
        'one'
        >>> Locale('ru').plural_form(100)
        'many'
        """
        return self._data.get('plural_form', _default_plural_rule)


def default_locale(category=None, aliases=LOCALE_ALIASES):
    """Returns the system default locale for a given category, based on
    environment variables.

    >>> for name in ['LANGUAGE', 'LC_ALL', 'LC_CTYPE']:
    ...     os.environ[name] = ''
    >>> os.environ['LANG'] = 'fr_FR.UTF-8'
    >>> default_locale('LC_MESSAGES')
    'fr_FR'

    The "C" or "POSIX" pseudo-locales are treated as aliases for the
    "en_US_POSIX" locale:

    >>> os.environ['LC_MESSAGES'] = 'POSIX'
    >>> default_locale('LC_MESSAGES')
    'en_US_POSIX'

    The following fallbacks to the variable are always considered:

    - ``LANGUAGE``
    - ``LC_ALL``
    - ``LC_CTYPE``
    - ``LANG``

    :param category: one of the ``LC_XXX`` environment variable names
    :param aliases: a dictionary of aliases for locale identifiers
    """
    varnames = (category, 'LANGUAGE', 'LC_ALL', 'LC_CTYPE', 'LANG')
    for name in filter(None, varnames):
        locale = os.getenv(name)
        if locale:
            if name == 'LANGUAGE' and ':' in locale:
                # the LANGUAGE variable may contain a colon-separated list of
                # language codes; we just pick the language on the list
                locale = locale.split(':')[0]
            if locale.split('.')[0] in ('C', 'POSIX'):
                locale = 'en_US_POSIX'
            elif aliases and locale in aliases:
                locale = aliases[locale]
            try:
                return get_locale_identifier(parse_locale(locale))
            except ValueError:
                pass


def negotiate_locale(preferred, available, sep='_', aliases=LOCALE_ALIASES):
    """Find the best match between available and requested locale strings.

    >>> negotiate_locale(['de_DE', 'en_US'], ['de_DE', 'de_AT'])
    'de_DE'
    >>> negotiate_locale(['de_DE', 'en_US'], ['en', 'de'])
    'de'

    Case is ignored by the algorithm, the result uses the case of the preferred
    locale identifier:

    >>> negotiate_locale(['de_DE', 'en_US'], ['de_de', 'de_at'])
    'de_DE'

    >>> negotiate_locale(['de_DE', 'en_US'], ['de_de', 'de_at'])
    'de_DE'

    By default, some web browsers unfortunately do not include the territory
    in the locale identifier for many locales, and some don't even allow the
    user to easily add the territory. So while you may prefer using qualified
    locale identifiers in your web-application, they would not normally match
    the language-only locale sent by such browsers. To workaround that, this
    function uses a default mapping of commonly used langauge-only locale
    identifiers to identifiers including the territory:

    >>> negotiate_locale(['ja', 'en_US'], ['ja_JP', 'en_US'])
    'ja_JP'

    Some browsers even use an incorrect or outdated language code, such as "no"
    for Norwegian, where the correct locale identifier would actually be "nb_NO"
    (Bokmål) or "nn_NO" (Nynorsk). The aliases are intended to take care of
    such cases, too:

    >>> negotiate_locale(['no', 'sv'], ['nb_NO', 'sv_SE'])
    'nb_NO'

    You can override this default mapping by passing a different `aliases`
    dictionary to this function, or you can bypass the behavior althogher by
    setting the `aliases` parameter to `None`.

    :param preferred: the list of locale strings preferred by the user
    :param available: the list of locale strings available
    :param sep: character that separates the different parts of the locale
                strings
    :param aliases: a dictionary of aliases for locale identifiers
    """
    available = [a.lower() for a in available if a]
    for locale in preferred:
        ll = locale.lower()
        if ll in available:
            return locale
        if aliases:
            alias = aliases.get(ll)
            if alias:
                alias = alias.replace('_', sep)
                if alias.lower() in available:
                    return alias
        parts = locale.split(sep)
        if len(parts) > 1 and parts[0].lower() in available:
            return parts[0]
    return None


def parse_locale(identifier, sep='_'):
    """Parse a locale identifier into a tuple of the form ``(language,
    territory, script, variant)``.

    >>> parse_locale('zh_CN')
    ('zh', 'CN', None, None)
    >>> parse_locale('zh_Hans_CN')
    ('zh', 'CN', 'Hans', None)

    The default component separator is "_", but a different separator can be
    specified using the `sep` parameter:

    >>> parse_locale('zh-CN', sep='-')
    ('zh', 'CN', None, None)

    If the identifier cannot be parsed into a locale, a `ValueError` exception
    is raised:

    >>> parse_locale('not_a_LOCALE_String')
    Traceback (most recent call last):
      ...
    ValueError: 'not_a_LOCALE_String' is not a valid locale identifier

    Encoding information and locale modifiers are removed from the identifier:

    >>> parse_locale('it_IT@euro')
    ('it', 'IT', None, None)
    >>> parse_locale('en_US.UTF-8')
    ('en', 'US', None, None)
    >>> parse_locale('de_DE.iso885915@euro')
    ('de', 'DE', None, None)

    See :rfc:`4646` for more information.

    :param identifier: the locale identifier string
    :param sep: character that separates the different components of the locale
                identifier
    :raise `ValueError`: if the string does not appear to be a valid locale
                         identifier
    """
    if '.' in identifier:
        # this is probably the charset/encoding, which we don't care about
        identifier = identifier.split('.', 1)[0]
    if '@' in identifier:
        # this is a locale modifier such as @euro, which we don't care about
        # either
        identifier = identifier.split('@', 1)[0]

    parts = identifier.split(sep)
    lang = parts.pop(0).lower()
    if not lang.isalpha():
        raise ValueError('expected only letters, got %r' % lang)

    script = territory = variant = None
    if parts:
        if len(parts[0]) == 4 and parts[0].isalpha():
            script = parts.pop(0).title()

    if parts:
        if len(parts[0]) == 2 and parts[0].isalpha():
            territory = parts.pop(0).upper()
        elif len(parts[0]) == 3 and parts[0].isdigit():
            territory = parts.pop(0)

    if parts:
        if len(parts[0]) == 4 and parts[0][0].isdigit() or \
                len(parts[0]) >= 5 and parts[0][0].isalpha():
            variant = parts.pop()

    if parts:
        raise ValueError('%r is not a valid locale identifier' % identifier)

    return lang, territory, script, variant


def get_locale_identifier(tup, sep='_'):
    """The reverse of :func:`parse_locale`.  It creates a locale identifier out
    of a ``(language, territory, script, variant)`` tuple.  Items can be set to
    ``None`` and trailing ``None``\s can also be left out of the tuple.

    >>> get_locale_identifier(('de', 'DE', None, '1999'))
    'de_DE_1999'

    .. versionadded:: 1.0

    :param tup: the tuple as returned by :func:`parse_locale`.
    :param sep: the separator for the identifier.
    """
    tup = tuple(tup[:4])
    lang, territory, script, variant = tup + (None,) * (4 - len(tup))
    return sep.join(filter(None, (lang, script, territory, variant)))

########NEW FILE########
__FILENAME__ = dates
# -*- coding: utf-8 -*-
"""
    babel.dates
    ~~~~~~~~~~~

    Locale dependent formatting and parsing of dates and times.

    The default locale for the functions in this module is determined by the
    following environment variables, in that order:

     * ``LC_TIME``,
     * ``LC_ALL``, and
     * ``LANG``

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import division

import re
import pytz as _pytz

from datetime import date, datetime, time, timedelta
from bisect import bisect_right

from babel.core import default_locale, get_global, Locale
from babel.util import UTC, LOCALTZ
from babel._compat import string_types, integer_types, number_types


LC_TIME = default_locale('LC_TIME')

# Aliases for use in scopes where the modules are shadowed by local variables
date_ = date
datetime_ = datetime
time_ = time


def get_timezone(zone=None):
    """Looks up a timezone by name and returns it.  The timezone object
    returned comes from ``pytz`` and corresponds to the `tzinfo` interface and
    can be used with all of the functions of Babel that operate with dates.

    If a timezone is not known a :exc:`LookupError` is raised.  If `zone`
    is ``None`` a local zone object is returned.

    :param zone: the name of the timezone to look up.  If a timezone object
                 itself is passed in, mit's returned unchanged.
    """
    if zone is None:
        return LOCALTZ
    if not isinstance(zone, string_types):
        return zone
    try:
        return _pytz.timezone(zone)
    except _pytz.UnknownTimeZoneError:
        raise LookupError('Unknown timezone %s' % zone)


def get_next_timezone_transition(zone=None, dt=None):
    """Given a timezone it will return a :class:`TimezoneTransition` object
    that holds the information about the next timezone transition that's going
    to happen.  For instance this can be used to detect when the next DST
    change is going to happen and how it looks like.

    The transition is calculated relative to the given datetime object.  The
    next transition that follows the date is used.  If a transition cannot
    be found the return value will be `None`.

    Transition information can only be provided for timezones returned by
    the :func:`get_timezone` function.

    :param zone: the timezone for which the transition should be looked up.
                 If not provided the local timezone is used.
    :param dt: the date after which the next transition should be found.
               If not given the current time is assumed.
    """
    zone = get_timezone(zone)
    if dt is None:
        dt = datetime.utcnow()
    else:
        dt = dt.replace(tzinfo=None)

    if not hasattr(zone, '_utc_transition_times'):
        raise TypeError('Given timezone does not have UTC transition '
                        'times.  This can happen because the operating '
                        'system fallback local timezone is used or a '
                        'custom timezone object')

    try:
        idx = max(0, bisect_right(zone._utc_transition_times, dt))
        old_trans = zone._transition_info[idx - 1]
        new_trans = zone._transition_info[idx]
        old_tz = zone._tzinfos[old_trans]
        new_tz = zone._tzinfos[new_trans]
    except (LookupError, ValueError):
        return None

    return TimezoneTransition(
        activates=zone._utc_transition_times[idx],
        from_tzinfo=old_tz,
        to_tzinfo=new_tz,
        reference_date=dt
    )


class TimezoneTransition(object):
    """A helper object that represents the return value from
    :func:`get_next_timezone_transition`.
    """

    def __init__(self, activates, from_tzinfo, to_tzinfo, reference_date=None):
        #: the time of the activation of the timezone transition in UTC.
        self.activates = activates
        #: the timezone from where the transition starts.
        self.from_tzinfo = from_tzinfo
        #: the timezone for after the transition.
        self.to_tzinfo = to_tzinfo
        #: the reference date that was provided.  This is the `dt` parameter
        #: to the :func:`get_next_timezone_transition`.
        self.reference_date = reference_date

    @property
    def from_tz(self):
        """The name of the timezone before the transition."""
        return self.from_tzinfo._tzname

    @property
    def to_tz(self):
        """The name of the timezone after the transition."""
        return self.to_tzinfo._tzname

    @property
    def from_offset(self):
        """The UTC offset in seconds before the transition."""
        return int(self.from_tzinfo._utcoffset.total_seconds())

    @property
    def to_offset(self):
        """The UTC offset in seconds after the transition."""
        return int(self.to_tzinfo._utcoffset.total_seconds())

    def __repr__(self):
        return '<TimezoneTransition %s -> %s (%s)>' % (
            self.from_tz,
            self.to_tz,
            self.activates,
        )


def get_period_names(locale=LC_TIME):
    """Return the names for day periods (AM/PM) used by the locale.

    >>> get_period_names(locale='en_US')['am']
    u'AM'

    :param locale: the `Locale` object, or a locale string
    """
    return Locale.parse(locale).periods


def get_day_names(width='wide', context='format', locale=LC_TIME):
    """Return the day names used by the locale for the specified format.

    >>> get_day_names('wide', locale='en_US')[1]
    u'Tuesday'
    >>> get_day_names('abbreviated', locale='es')[1]
    u'mar'
    >>> get_day_names('narrow', context='stand-alone', locale='de_DE')[1]
    u'D'

    :param width: the width to use, one of "wide", "abbreviated", or "narrow"
    :param context: the context, either "format" or "stand-alone"
    :param locale: the `Locale` object, or a locale string
    """
    return Locale.parse(locale).days[context][width]


def get_month_names(width='wide', context='format', locale=LC_TIME):
    """Return the month names used by the locale for the specified format.

    >>> get_month_names('wide', locale='en_US')[1]
    u'January'
    >>> get_month_names('abbreviated', locale='es')[1]
    u'ene'
    >>> get_month_names('narrow', context='stand-alone', locale='de_DE')[1]
    u'J'

    :param width: the width to use, one of "wide", "abbreviated", or "narrow"
    :param context: the context, either "format" or "stand-alone"
    :param locale: the `Locale` object, or a locale string
    """
    return Locale.parse(locale).months[context][width]


def get_quarter_names(width='wide', context='format', locale=LC_TIME):
    """Return the quarter names used by the locale for the specified format.

    >>> get_quarter_names('wide', locale='en_US')[1]
    u'1st quarter'
    >>> get_quarter_names('abbreviated', locale='de_DE')[1]
    u'Q1'

    :param width: the width to use, one of "wide", "abbreviated", or "narrow"
    :param context: the context, either "format" or "stand-alone"
    :param locale: the `Locale` object, or a locale string
    """
    return Locale.parse(locale).quarters[context][width]


def get_era_names(width='wide', locale=LC_TIME):
    """Return the era names used by the locale for the specified format.

    >>> get_era_names('wide', locale='en_US')[1]
    u'Anno Domini'
    >>> get_era_names('abbreviated', locale='de_DE')[1]
    u'n. Chr.'

    :param width: the width to use, either "wide", "abbreviated", or "narrow"
    :param locale: the `Locale` object, or a locale string
    """
    return Locale.parse(locale).eras[width]


def get_date_format(format='medium', locale=LC_TIME):
    """Return the date formatting patterns used by the locale for the specified
    format.

    >>> get_date_format(locale='en_US')
    <DateTimePattern u'MMM d, y'>
    >>> get_date_format('full', locale='de_DE')
    <DateTimePattern u'EEEE, d. MMMM y'>

    :param format: the format to use, one of "full", "long", "medium", or
                   "short"
    :param locale: the `Locale` object, or a locale string
    """
    return Locale.parse(locale).date_formats[format]


def get_datetime_format(format='medium', locale=LC_TIME):
    """Return the datetime formatting patterns used by the locale for the
    specified format.

    >>> get_datetime_format(locale='en_US')
    u'{1}, {0}'

    :param format: the format to use, one of "full", "long", "medium", or
                   "short"
    :param locale: the `Locale` object, or a locale string
    """
    patterns = Locale.parse(locale).datetime_formats
    if format not in patterns:
        format = None
    return patterns[format]


def get_time_format(format='medium', locale=LC_TIME):
    """Return the time formatting patterns used by the locale for the specified
    format.

    >>> get_time_format(locale='en_US')
    <DateTimePattern u'h:mm:ss a'>
    >>> get_time_format('full', locale='de_DE')
    <DateTimePattern u'HH:mm:ss zzzz'>

    :param format: the format to use, one of "full", "long", "medium", or
                   "short"
    :param locale: the `Locale` object, or a locale string
    """
    return Locale.parse(locale).time_formats[format]


def get_timezone_gmt(datetime=None, width='long', locale=LC_TIME):
    """Return the timezone associated with the given `datetime` object formatted
    as string indicating the offset from GMT.

    >>> dt = datetime(2007, 4, 1, 15, 30)
    >>> get_timezone_gmt(dt, locale='en')
    u'GMT+00:00'

    >>> tz = get_timezone('America/Los_Angeles')
    >>> dt = datetime(2007, 4, 1, 15, 30, tzinfo=tz)
    >>> get_timezone_gmt(dt, locale='en')
    u'GMT-08:00'
    >>> get_timezone_gmt(dt, 'short', locale='en')
    u'-0800'

    The long format depends on the locale, for example in France the acronym
    UTC string is used instead of GMT:

    >>> get_timezone_gmt(dt, 'long', locale='fr_FR')
    u'UTC-08:00'

    .. versionadded:: 0.9

    :param datetime: the ``datetime`` object; if `None`, the current date and
                     time in UTC is used
    :param width: either "long" or "short"
    :param locale: the `Locale` object, or a locale string
    """
    if datetime is None:
        datetime = datetime_.utcnow()
    elif isinstance(datetime, integer_types):
        datetime = datetime_.utcfromtimestamp(datetime).time()
    if datetime.tzinfo is None:
        datetime = datetime.replace(tzinfo=UTC)
    locale = Locale.parse(locale)

    offset = datetime.tzinfo.utcoffset(datetime)
    seconds = offset.days * 24 * 60 * 60 + offset.seconds
    hours, seconds = divmod(seconds, 3600)
    if width == 'short':
        pattern = u'%+03d%02d'
    else:
        pattern = locale.zone_formats['gmt'] % '%+03d:%02d'
    return pattern % (hours, seconds // 60)


def get_timezone_location(dt_or_tzinfo=None, locale=LC_TIME):
    """Return a representation of the given timezone using "location format".

    The result depends on both the local display name of the country and the
    city associated with the time zone:

    >>> tz = get_timezone('America/St_Johns')
    >>> get_timezone_location(tz, locale='de_DE')
    u"Kanada (St. John's) Zeit"
    >>> tz = get_timezone('America/Mexico_City')
    >>> get_timezone_location(tz, locale='de_DE')
    u'Mexiko (Mexiko-Stadt) Zeit'

    If the timezone is associated with a country that uses only a single
    timezone, just the localized country name is returned:

    >>> tz = get_timezone('Europe/Berlin')
    >>> get_timezone_name(tz, locale='de_DE')
    u'Mitteleurop\\xe4ische Zeit'

    .. versionadded:: 0.9

    :param dt_or_tzinfo: the ``datetime`` or ``tzinfo`` object that determines
                         the timezone; if `None`, the current date and time in
                         UTC is assumed
    :param locale: the `Locale` object, or a locale string
    :return: the localized timezone name using location format
    """
    if dt_or_tzinfo is None:
        dt = datetime.now()
        tzinfo = LOCALTZ
    elif isinstance(dt_or_tzinfo, string_types):
        dt = None
        tzinfo = get_timezone(dt_or_tzinfo)
    elif isinstance(dt_or_tzinfo, integer_types):
        dt = None
        tzinfo = UTC
    elif isinstance(dt_or_tzinfo, (datetime, time)):
        dt = dt_or_tzinfo
        if dt.tzinfo is not None:
            tzinfo = dt.tzinfo
        else:
            tzinfo = UTC
    else:
        dt = None
        tzinfo = dt_or_tzinfo
    locale = Locale.parse(locale)

    if hasattr(tzinfo, 'zone'):
        zone = tzinfo.zone
    else:
        zone = tzinfo.tzname(dt or datetime.utcnow())

    # Get the canonical time-zone code
    zone = get_global('zone_aliases').get(zone, zone)

    info = locale.time_zones.get(zone, {})

    # Otherwise, if there is only one timezone for the country, return the
    # localized country name
    region_format = locale.zone_formats['region']
    territory = get_global('zone_territories').get(zone)
    if territory not in locale.territories:
        territory = 'ZZ' # invalid/unknown
    territory_name = locale.territories[territory]
    if territory and len(get_global('territory_zones').get(territory, [])) == 1:
        return region_format % (territory_name)

    # Otherwise, include the city in the output
    fallback_format = locale.zone_formats['fallback']
    if 'city' in info:
        city_name = info['city']
    else:
        metazone = get_global('meta_zones').get(zone)
        metazone_info = locale.meta_zones.get(metazone, {})
        if 'city' in metazone_info:
            city_name = metazone_info['city']
        elif '/' in zone:
            city_name = zone.split('/', 1)[1].replace('_', ' ')
        else:
            city_name = zone.replace('_', ' ')

    return region_format % (fallback_format % {
        '0': city_name,
        '1': territory_name
    })


def get_timezone_name(dt_or_tzinfo=None, width='long', uncommon=False,
                      locale=LC_TIME, zone_variant=None):
    r"""Return the localized display name for the given timezone. The timezone
    may be specified using a ``datetime`` or `tzinfo` object.

    >>> dt = time(15, 30, tzinfo=get_timezone('America/Los_Angeles'))
    >>> get_timezone_name(dt, locale='en_US')
    u'Pacific Standard Time'
    >>> get_timezone_name(dt, width='short', locale='en_US')
    u'PST'

    If this function gets passed only a `tzinfo` object and no concrete
    `datetime`,  the returned display name is indenpendent of daylight savings
    time. This can be used for example for selecting timezones, or to set the
    time of events that recur across DST changes:

    >>> tz = get_timezone('America/Los_Angeles')
    >>> get_timezone_name(tz, locale='en_US')
    u'Pacific Time'
    >>> get_timezone_name(tz, 'short', locale='en_US')
    u'PT'

    If no localized display name for the timezone is available, and the timezone
    is associated with a country that uses only a single timezone, the name of
    that country is returned, formatted according to the locale:

    >>> tz = get_timezone('Europe/Berlin')
    >>> get_timezone_name(tz, locale='de_DE')
    u'Mitteleurop\xe4ische Zeit'
    >>> get_timezone_name(tz, locale='pt_BR')
    u'Hor\xe1rio da Europa Central'

    On the other hand, if the country uses multiple timezones, the city is also
    included in the representation:

    >>> tz = get_timezone('America/St_Johns')
    >>> get_timezone_name(tz, locale='de_DE')
    u'Neufundland-Zeit'

    Note that short format is currently not supported for all timezones and
    all locales.  This is partially because not every timezone has a short
    code in every locale.  In that case it currently falls back to the long
    format.

    For more information see `LDML Appendix J: Time Zone Display Names
    <http://www.unicode.org/reports/tr35/#Time_Zone_Fallback>`_

    .. versionadded:: 0.9

    .. versionchanged:: 1.0
       Added `zone_variant` support.

    :param dt_or_tzinfo: the ``datetime`` or ``tzinfo`` object that determines
                         the timezone; if a ``tzinfo`` object is used, the
                         resulting display name will be generic, i.e.
                         independent of daylight savings time; if `None`, the
                         current date in UTC is assumed
    :param width: either "long" or "short"
    :param uncommon: deprecated and ignored
    :param zone_variant: defines the zone variation to return.  By default the
                           variation is defined from the datetime object
                           passed in.  If no datetime object is passed in, the
                           ``'generic'`` variation is assumed.  The following
                           values are valid: ``'generic'``, ``'daylight'`` and
                           ``'standard'``.
    :param locale: the `Locale` object, or a locale string
    """
    if dt_or_tzinfo is None:
        dt = datetime.now()
        tzinfo = LOCALTZ
    elif isinstance(dt_or_tzinfo, string_types):
        dt = None
        tzinfo = get_timezone(dt_or_tzinfo)
    elif isinstance(dt_or_tzinfo, integer_types):
        dt = None
        tzinfo = UTC
    elif isinstance(dt_or_tzinfo, (datetime, time)):
        dt = dt_or_tzinfo
        if dt.tzinfo is not None:
            tzinfo = dt.tzinfo
        else:
            tzinfo = UTC
    else:
        dt = None
        tzinfo = dt_or_tzinfo
    locale = Locale.parse(locale)

    if hasattr(tzinfo, 'zone'):
        zone = tzinfo.zone
    else:
        zone = tzinfo.tzname(dt)

    if zone_variant is None:
        if dt is None:
            zone_variant = 'generic'
        else:
            dst = tzinfo.dst(dt)
            if dst:
                zone_variant = 'daylight'
            else:
                zone_variant = 'standard'
    else:
        if zone_variant not in ('generic', 'standard', 'daylight'):
            raise ValueError('Invalid zone variation')

    # Get the canonical time-zone code
    zone = get_global('zone_aliases').get(zone, zone)

    info = locale.time_zones.get(zone, {})
    # Try explicitly translated zone names first
    if width in info:
        if zone_variant in info[width]:
            return info[width][zone_variant]

    metazone = get_global('meta_zones').get(zone)
    if metazone:
        metazone_info = locale.meta_zones.get(metazone, {})
        if width in metazone_info:
            if zone_variant in metazone_info[width]:
                return metazone_info[width][zone_variant]

    # If we have a concrete datetime, we assume that the result can't be
    # independent of daylight savings time, so we return the GMT offset
    if dt is not None:
        return get_timezone_gmt(dt, width=width, locale=locale)

    return get_timezone_location(dt_or_tzinfo, locale=locale)


def format_date(date=None, format='medium', locale=LC_TIME):
    """Return a date formatted according to the given pattern.

    >>> d = date(2007, 04, 01)
    >>> format_date(d, locale='en_US')
    u'Apr 1, 2007'
    >>> format_date(d, format='full', locale='de_DE')
    u'Sonntag, 1. April 2007'

    If you don't want to use the locale default formats, you can specify a
    custom date pattern:

    >>> format_date(d, "EEE, MMM d, ''yy", locale='en')
    u"Sun, Apr 1, '07"

    :param date: the ``date`` or ``datetime`` object; if `None`, the current
                 date is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param locale: a `Locale` object or a locale identifier
    """
    if date is None:
        date = date_.today()
    elif isinstance(date, datetime):
        date = date.date()

    locale = Locale.parse(locale)
    if format in ('full', 'long', 'medium', 'short'):
        format = get_date_format(format, locale=locale)
    pattern = parse_pattern(format)
    return pattern.apply(date, locale)


def format_datetime(datetime=None, format='medium', tzinfo=None,
                    locale=LC_TIME):
    r"""Return a date formatted according to the given pattern.

    >>> dt = datetime(2007, 04, 01, 15, 30)
    >>> format_datetime(dt, locale='en_US')
    u'Apr 1, 2007, 3:30:00 PM'

    For any pattern requiring the display of the time-zone, the third-party
    ``pytz`` package is needed to explicitly specify the time-zone:

    >>> format_datetime(dt, 'full', tzinfo=get_timezone('Europe/Paris'),
    ...                 locale='fr_FR')
    u'dimanche 1 avril 2007 17:30:00 heure avanc\xe9e d\u2019Europe centrale'
    >>> format_datetime(dt, "yyyy.MM.dd G 'at' HH:mm:ss zzz",
    ...                 tzinfo=get_timezone('US/Eastern'), locale='en')
    u'2007.04.01 AD at 11:30:00 EDT'

    :param datetime: the `datetime` object; if `None`, the current date and
                     time is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param tzinfo: the timezone to apply to the time for display
    :param locale: a `Locale` object or a locale identifier
    """
    if datetime is None:
        datetime = datetime_.utcnow()
    elif isinstance(datetime, number_types):
        datetime = datetime_.utcfromtimestamp(datetime)
    elif isinstance(datetime, time):
        datetime = datetime_.combine(date.today(), datetime)
    if datetime.tzinfo is None:
        datetime = datetime.replace(tzinfo=UTC)
    if tzinfo is not None:
        datetime = datetime.astimezone(get_timezone(tzinfo))
        if hasattr(tzinfo, 'normalize'): # pytz
            datetime = tzinfo.normalize(datetime)

    locale = Locale.parse(locale)
    if format in ('full', 'long', 'medium', 'short'):
        return get_datetime_format(format, locale=locale) \
            .replace("'", "") \
            .replace('{0}', format_time(datetime, format, tzinfo=None,
                                        locale=locale)) \
            .replace('{1}', format_date(datetime, format, locale=locale))
    else:
        return parse_pattern(format).apply(datetime, locale)


def format_time(time=None, format='medium', tzinfo=None, locale=LC_TIME):
    r"""Return a time formatted according to the given pattern.

    >>> t = time(15, 30)
    >>> format_time(t, locale='en_US')
    u'3:30:00 PM'
    >>> format_time(t, format='short', locale='de_DE')
    u'15:30'

    If you don't want to use the locale default formats, you can specify a
    custom time pattern:

    >>> format_time(t, "hh 'o''clock' a", locale='en')
    u"03 o'clock PM"

    For any pattern requiring the display of the time-zone a
    timezone has to be specified explicitly:

    >>> t = datetime(2007, 4, 1, 15, 30)
    >>> tzinfo = get_timezone('Europe/Paris')
    >>> t = tzinfo.localize(t)
    >>> format_time(t, format='full', tzinfo=tzinfo, locale='fr_FR')
    u'15:30:00 heure avanc\xe9e d\u2019Europe centrale'
    >>> format_time(t, "hh 'o''clock' a, zzzz", tzinfo=get_timezone('US/Eastern'),
    ...             locale='en')
    u"09 o'clock AM, Eastern Daylight Time"

    As that example shows, when this function gets passed a
    ``datetime.datetime`` value, the actual time in the formatted string is
    adjusted to the timezone specified by the `tzinfo` parameter. If the
    ``datetime`` is "naive" (i.e. it has no associated timezone information),
    it is assumed to be in UTC.

    These timezone calculations are **not** performed if the value is of type
    ``datetime.time``, as without date information there's no way to determine
    what a given time would translate to in a different timezone without
    information about whether daylight savings time is in effect or not. This
    means that time values are left as-is, and the value of the `tzinfo`
    parameter is only used to display the timezone name if needed:

    >>> t = time(15, 30)
    >>> format_time(t, format='full', tzinfo=get_timezone('Europe/Paris'),
    ...             locale='fr_FR')
    u'15:30:00 heure normale de l\u2019Europe centrale'
    >>> format_time(t, format='full', tzinfo=get_timezone('US/Eastern'),
    ...             locale='en_US')
    u'3:30:00 PM Eastern Standard Time'

    :param time: the ``time`` or ``datetime`` object; if `None`, the current
                 time in UTC is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param tzinfo: the time-zone to apply to the time for display
    :param locale: a `Locale` object or a locale identifier
    """
    if time is None:
        time = datetime.utcnow()
    elif isinstance(time, number_types):
        time = datetime.utcfromtimestamp(time)
    if time.tzinfo is None:
        time = time.replace(tzinfo=UTC)
    if isinstance(time, datetime):
        if tzinfo is not None:
            time = time.astimezone(tzinfo)
            if hasattr(tzinfo, 'normalize'): # pytz
                time = tzinfo.normalize(time)
        time = time.timetz()
    elif tzinfo is not None:
        time = time.replace(tzinfo=tzinfo)

    locale = Locale.parse(locale)
    if format in ('full', 'long', 'medium', 'short'):
        format = get_time_format(format, locale=locale)
    return parse_pattern(format).apply(time, locale)


TIMEDELTA_UNITS = (
    ('year',   3600 * 24 * 365),
    ('month',  3600 * 24 * 30),
    ('week',   3600 * 24 * 7),
    ('day',    3600 * 24),
    ('hour',   3600),
    ('minute', 60),
    ('second', 1)
)


def format_timedelta(delta, granularity='second', threshold=.85,
                     add_direction=False, format='medium',
                     locale=LC_TIME):
    """Return a time delta according to the rules of the given locale.

    >>> format_timedelta(timedelta(weeks=12), locale='en_US')
    u'3 months'
    >>> format_timedelta(timedelta(seconds=1), locale='es')
    u'1 segundo'

    The granularity parameter can be provided to alter the lowest unit
    presented, which defaults to a second.

    >>> format_timedelta(timedelta(hours=3), granularity='day',
    ...                  locale='en_US')
    u'1 day'

    The threshold parameter can be used to determine at which value the
    presentation switches to the next higher unit. A higher threshold factor
    means the presentation will switch later. For example:

    >>> format_timedelta(timedelta(hours=23), threshold=0.9, locale='en_US')
    u'1 day'
    >>> format_timedelta(timedelta(hours=23), threshold=1.1, locale='en_US')
    u'23 hours'

    In addition directional information can be provided that informs
    the user if the date is in the past or in the future:

    >>> format_timedelta(timedelta(hours=1), add_direction=True, locale='en')
    u'In 1 hour'
    >>> format_timedelta(timedelta(hours=-1), add_direction=True, locale='en')
    u'1 hour ago'

    :param delta: a ``timedelta`` object representing the time difference to
                  format, or the delta in seconds as an `int` value
    :param granularity: determines the smallest unit that should be displayed,
                        the value can be one of "year", "month", "week", "day",
                        "hour", "minute" or "second"
    :param threshold: factor that determines at which point the presentation
                      switches to the next higher unit
    :param add_direction: if this flag is set to `True` the return value will
                          include directional information.  For instance a
                          positive timedelta will include the information about
                          it being in the future, a negative will be information
                          about the value being in the past.
    :param format: the format (currently only "medium" and "short" are supported)
    :param locale: a `Locale` object or a locale identifier
    """
    if format not in ('short', 'medium'):
        raise TypeError('Format can only be one of "short" or "medium"')
    if isinstance(delta, timedelta):
        seconds = int((delta.days * 86400) + delta.seconds)
    else:
        seconds = delta
    locale = Locale.parse(locale)

    def _iter_choices(unit):
        if add_direction:
            if seconds >= 0:
                yield unit + '-future'
            else:
                yield unit + '-past'
        yield unit + ':' + format
        yield unit

    for unit, secs_per_unit in TIMEDELTA_UNITS:
        value = abs(seconds) / secs_per_unit
        if value >= threshold or unit == granularity:
            if unit == granularity and value > 0:
                value = max(1, value)
            value = int(round(value))
            plural_form = locale.plural_form(value)
            pattern = None
            for choice in _iter_choices(unit):
                patterns = locale._data['unit_patterns'].get(choice)
                if patterns is not None:
                    pattern = patterns[plural_form]
                    break
            # This really should not happen
            if pattern is None:
                return u''
            return pattern.replace('{0}', str(value))

    return u''


def parse_date(string, locale=LC_TIME):
    """Parse a date from a string.

    This function uses the date format for the locale as a hint to determine
    the order in which the date fields appear in the string.

    >>> parse_date('4/1/04', locale='en_US')
    datetime.date(2004, 4, 1)
    >>> parse_date('01.04.2004', locale='de_DE')
    datetime.date(2004, 4, 1)

    :param string: the string containing the date
    :param locale: a `Locale` object or a locale identifier
    """
    # TODO: try ISO format first?
    format = get_date_format(locale=locale).pattern.lower()
    year_idx = format.index('y')
    month_idx = format.index('m')
    if month_idx < 0:
        month_idx = format.index('l')
    day_idx = format.index('d')

    indexes = [(year_idx, 'Y'), (month_idx, 'M'), (day_idx, 'D')]
    indexes.sort()
    indexes = dict([(item[1], idx) for idx, item in enumerate(indexes)])

    # FIXME: this currently only supports numbers, but should also support month
    #        names, both in the requested locale, and english

    numbers = re.findall('(\d+)', string)
    year = numbers[indexes['Y']]
    if len(year) == 2:
        year = 2000 + int(year)
    else:
        year = int(year)
    month = int(numbers[indexes['M']])
    day = int(numbers[indexes['D']])
    if month > 12:
        month, day = day, month
    return date(year, month, day)


def parse_time(string, locale=LC_TIME):
    """Parse a time from a string.

    This function uses the time format for the locale as a hint to determine
    the order in which the time fields appear in the string.

    >>> parse_time('15:30:00', locale='en_US')
    datetime.time(15, 30)

    :param string: the string containing the time
    :param locale: a `Locale` object or a locale identifier
    :return: the parsed time
    :rtype: `time`
    """
    # TODO: try ISO format first?
    format = get_time_format(locale=locale).pattern.lower()
    hour_idx = format.index('h')
    if hour_idx < 0:
        hour_idx = format.index('k')
    min_idx = format.index('m')
    sec_idx = format.index('s')

    indexes = [(hour_idx, 'H'), (min_idx, 'M'), (sec_idx, 'S')]
    indexes.sort()
    indexes = dict([(item[1], idx) for idx, item in enumerate(indexes)])

    # FIXME: support 12 hour clock, and 0-based hour specification
    #        and seconds should be optional, maybe minutes too
    #        oh, and time-zones, of course

    numbers = re.findall('(\d+)', string)
    hour = int(numbers[indexes['H']])
    minute = int(numbers[indexes['M']])
    second = int(numbers[indexes['S']])
    return time(hour, minute, second)


class DateTimePattern(object):

    def __init__(self, pattern, format):
        self.pattern = pattern
        self.format = format

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.pattern)

    def __unicode__(self):
        return self.pattern

    def __mod__(self, other):
        if type(other) is not DateTimeFormat:
            return NotImplemented
        return self.format % other

    def apply(self, datetime, locale):
        return self % DateTimeFormat(datetime, locale)


class DateTimeFormat(object):

    def __init__(self, value, locale):
        assert isinstance(value, (date, datetime, time))
        if isinstance(value, (datetime, time)) and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        self.value = value
        self.locale = Locale.parse(locale)

    def __getitem__(self, name):
        char = name[0]
        num = len(name)
        if char == 'G':
            return self.format_era(char, num)
        elif char in ('y', 'Y', 'u'):
            return self.format_year(char, num)
        elif char in ('Q', 'q'):
            return self.format_quarter(char, num)
        elif char in ('M', 'L'):
            return self.format_month(char, num)
        elif char in ('w', 'W'):
            return self.format_week(char, num)
        elif char == 'd':
            return self.format(self.value.day, num)
        elif char == 'D':
            return self.format_day_of_year(num)
        elif char == 'F':
            return self.format_day_of_week_in_month()
        elif char in ('E', 'e', 'c'):
            return self.format_weekday(char, num)
        elif char == 'a':
            return self.format_period(char)
        elif char == 'h':
            if self.value.hour % 12 == 0:
                return self.format(12, num)
            else:
                return self.format(self.value.hour % 12, num)
        elif char == 'H':
            return self.format(self.value.hour, num)
        elif char == 'K':
            return self.format(self.value.hour % 12, num)
        elif char == 'k':
            if self.value.hour == 0:
                return self.format(24, num)
            else:
                return self.format(self.value.hour, num)
        elif char == 'm':
            return self.format(self.value.minute, num)
        elif char == 's':
            return self.format(self.value.second, num)
        elif char == 'S':
            return self.format_frac_seconds(num)
        elif char == 'A':
            return self.format_milliseconds_in_day(num)
        elif char in ('z', 'Z', 'v', 'V'):
            return self.format_timezone(char, num)
        else:
            raise KeyError('Unsupported date/time field %r' % char)

    def format_era(self, char, num):
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[max(3, num)]
        era = int(self.value.year >= 0)
        return get_era_names(width, self.locale)[era]

    def format_year(self, char, num):
        value = self.value.year
        if char.isupper():
            week = self.get_week_number(self.get_day_of_year())
            if week == 0:
                value -= 1
        year = self.format(value, num)
        if num == 2:
            year = year[-2:]
        return year

    def format_quarter(self, char, num):
        quarter = (self.value.month - 1) // 3 + 1
        if num <= 2:
            return ('%%0%dd' % num) % quarter
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[num]
        context = {'Q': 'format', 'q': 'stand-alone'}[char]
        return get_quarter_names(width, context, self.locale)[quarter]

    def format_month(self, char, num):
        if num <= 2:
            return ('%%0%dd' % num) % self.value.month
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[num]
        context = {'M': 'format', 'L': 'stand-alone'}[char]
        return get_month_names(width, context, self.locale)[self.value.month]

    def format_week(self, char, num):
        if char.islower(): # week of year
            day_of_year = self.get_day_of_year()
            week = self.get_week_number(day_of_year)
            if week == 0:
                date = self.value - timedelta(days=day_of_year)
                week = self.get_week_number(self.get_day_of_year(date),
                                            date.weekday())
            return self.format(week, num)
        else: # week of month
            week = self.get_week_number(self.value.day)
            if week == 0:
                date = self.value - timedelta(days=self.value.day)
                week = self.get_week_number(date.day, date.weekday())
                pass
            return '%d' % week

    def format_weekday(self, char, num):
        if num < 3:
            if char.islower():
                value = 7 - self.locale.first_week_day + self.value.weekday()
                return self.format(value % 7 + 1, num)
            num = 3
        weekday = self.value.weekday()
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[num]
        context = {3: 'format', 4: 'format', 5: 'stand-alone'}[num]
        return get_day_names(width, context, self.locale)[weekday]

    def format_day_of_year(self, num):
        return self.format(self.get_day_of_year(), num)

    def format_day_of_week_in_month(self):
        return '%d' % ((self.value.day - 1) // 7 + 1)

    def format_period(self, char):
        period = {0: 'am', 1: 'pm'}[int(self.value.hour >= 12)]
        return get_period_names(locale=self.locale)[period]

    def format_frac_seconds(self, num):
        value = str(self.value.microsecond)
        return self.format(round(float('.%s' % value), num) * 10**num, num)

    def format_milliseconds_in_day(self, num):
        msecs = self.value.microsecond // 1000 + self.value.second * 1000 + \
                self.value.minute * 60000 + self.value.hour * 3600000
        return self.format(msecs, num)

    def format_timezone(self, char, num):
        width = {3: 'short', 4: 'long'}[max(3, num)]
        if char == 'z':
            return get_timezone_name(self.value, width, locale=self.locale)
        elif char == 'Z':
            return get_timezone_gmt(self.value, width, locale=self.locale)
        elif char == 'v':
            return get_timezone_name(self.value.tzinfo, width,
                                     locale=self.locale)
        elif char == 'V':
            if num == 1:
                return get_timezone_name(self.value.tzinfo, width,
                                         uncommon=True, locale=self.locale)
            return get_timezone_location(self.value.tzinfo, locale=self.locale)

    def format(self, value, length):
        return ('%%0%dd' % length) % value

    def get_day_of_year(self, date=None):
        if date is None:
            date = self.value
        return (date - date.replace(month=1, day=1)).days + 1

    def get_week_number(self, day_of_period, day_of_week=None):
        """Return the number of the week of a day within a period. This may be
        the week number in a year or the week number in a month.

        Usually this will return a value equal to or greater than 1, but if the
        first week of the period is so short that it actually counts as the last
        week of the previous period, this function will return 0.

        >>> format = DateTimeFormat(date(2006, 1, 8), Locale.parse('de_DE'))
        >>> format.get_week_number(6)
        1

        >>> format = DateTimeFormat(date(2006, 1, 8), Locale.parse('en_US'))
        >>> format.get_week_number(6)
        2

        :param day_of_period: the number of the day in the period (usually
                              either the day of month or the day of year)
        :param day_of_week: the week day; if ommitted, the week day of the
                            current date is assumed
        """
        if day_of_week is None:
            day_of_week = self.value.weekday()
        first_day = (day_of_week - self.locale.first_week_day -
                     day_of_period + 1) % 7
        if first_day < 0:
            first_day += 7
        week_number = (day_of_period + first_day - 1) // 7
        if 7 - first_day >= self.locale.min_week_days:
            week_number += 1
        return week_number


PATTERN_CHARS = {
    'G': [1, 2, 3, 4, 5],                                           # era
    'y': None, 'Y': None, 'u': None,                                # year
    'Q': [1, 2, 3, 4], 'q': [1, 2, 3, 4],                           # quarter
    'M': [1, 2, 3, 4, 5], 'L': [1, 2, 3, 4, 5],                     # month
    'w': [1, 2], 'W': [1],                                          # week
    'd': [1, 2], 'D': [1, 2, 3], 'F': [1], 'g': None,               # day
    'E': [1, 2, 3, 4, 5], 'e': [1, 2, 3, 4, 5], 'c': [1, 3, 4, 5],  # week day
    'a': [1],                                                       # period
    'h': [1, 2], 'H': [1, 2], 'K': [1, 2], 'k': [1, 2],             # hour
    'm': [1, 2],                                                    # minute
    's': [1, 2], 'S': None, 'A': None,                              # second
    'z': [1, 2, 3, 4], 'Z': [1, 2, 3, 4], 'v': [1, 4], 'V': [1, 4]  # zone
}


def parse_pattern(pattern):
    """Parse date, time, and datetime format patterns.

    >>> parse_pattern("MMMMd").format
    u'%(MMMM)s%(d)s'
    >>> parse_pattern("MMM d, yyyy").format
    u'%(MMM)s %(d)s, %(yyyy)s'

    Pattern can contain literal strings in single quotes:

    >>> parse_pattern("H:mm' Uhr 'z").format
    u'%(H)s:%(mm)s Uhr %(z)s'

    An actual single quote can be used by using two adjacent single quote
    characters:

    >>> parse_pattern("hh' o''clock'").format
    u"%(hh)s o'clock"

    :param pattern: the formatting pattern to parse
    """
    if type(pattern) is DateTimePattern:
        return pattern

    result = []
    quotebuf = None
    charbuf = []
    fieldchar = ['']
    fieldnum = [0]

    def append_chars():
        result.append(''.join(charbuf).replace('%', '%%'))
        del charbuf[:]

    def append_field():
        limit = PATTERN_CHARS[fieldchar[0]]
        if limit and fieldnum[0] not in limit:
            raise ValueError('Invalid length for field: %r'
                             % (fieldchar[0] * fieldnum[0]))
        result.append('%%(%s)s' % (fieldchar[0] * fieldnum[0]))
        fieldchar[0] = ''
        fieldnum[0] = 0

    for idx, char in enumerate(pattern.replace("''", '\0')):
        if quotebuf is None:
            if char == "'": # quote started
                if fieldchar[0]:
                    append_field()
                elif charbuf:
                    append_chars()
                quotebuf = []
            elif char in PATTERN_CHARS:
                if charbuf:
                    append_chars()
                if char == fieldchar[0]:
                    fieldnum[0] += 1
                else:
                    if fieldchar[0]:
                        append_field()
                    fieldchar[0] = char
                    fieldnum[0] = 1
            else:
                if fieldchar[0]:
                    append_field()
                charbuf.append(char)

        elif quotebuf is not None:
            if char == "'": # end of quote
                charbuf.extend(quotebuf)
                quotebuf = None
            else: # inside quote
                quotebuf.append(char)

    if fieldchar[0]:
        append_field()
    elif charbuf:
        append_chars()

    return DateTimePattern(pattern, u''.join(result).replace('\0', "'"))

########NEW FILE########
__FILENAME__ = localedata
# -*- coding: utf-8 -*-
"""
    babel.localedata
    ~~~~~~~~~~~~~~~~

    Low-level locale data access.

    :note: The `Locale` class, which uses this module under the hood, provides a
           more convenient interface for accessing the locale data.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import os
import threading
from collections import MutableMapping

from babel._compat import pickle


_cache = {}
_cache_lock = threading.RLock()
_dirname = os.path.join(os.path.dirname(__file__), 'localedata')


def exists(name):
    """Check whether locale data is available for the given locale.  Ther
    return value is `True` if it exists, `False` otherwise.

    :param name: the locale identifier string
    """
    if name in _cache:
        return True
    return os.path.exists(os.path.join(_dirname, '%s.dat' % name))


def locale_identifiers():
    """Return a list of all locale identifiers for which locale data is
    available.

    .. versionadded:: 0.8.1

    :return: a list of locale identifiers (strings)
    """
    return [stem for stem, extension in [
        os.path.splitext(filename) for filename in os.listdir(_dirname)
    ] if extension == '.dat' and stem != 'root']


def load(name, merge_inherited=True):
    """Load the locale data for the given locale.

    The locale data is a dictionary that contains much of the data defined by
    the Common Locale Data Repository (CLDR). This data is stored as a
    collection of pickle files inside the ``babel`` package.

    >>> d = load('en_US')
    >>> d['languages']['sv']
    u'Swedish'

    Note that the results are cached, and subsequent requests for the same
    locale return the same dictionary:

    >>> d1 = load('en_US')
    >>> d2 = load('en_US')
    >>> d1 is d2
    True

    :param name: the locale identifier string (or "root")
    :param merge_inherited: whether the inherited data should be merged into
                            the data of the requested locale
    :raise `IOError`: if no locale data file is found for the given locale
                      identifer, or one of the locales it inherits from
    """
    _cache_lock.acquire()
    try:
        data = _cache.get(name)
        if not data:
            # Load inherited data
            if name == 'root' or not merge_inherited:
                data = {}
            else:
                parts = name.split('_')
                if len(parts) == 1:
                    parent = 'root'
                else:
                    parent = '_'.join(parts[:-1])
                data = load(parent).copy()
            filename = os.path.join(_dirname, '%s.dat' % name)
            fileobj = open(filename, 'rb')
            try:
                if name != 'root' and merge_inherited:
                    merge(data, pickle.load(fileobj))
                else:
                    data = pickle.load(fileobj)
                _cache[name] = data
            finally:
                fileobj.close()
        return data
    finally:
        _cache_lock.release()


def merge(dict1, dict2):
    """Merge the data from `dict2` into the `dict1` dictionary, making copies
    of nested dictionaries.

    >>> d = {1: 'foo', 3: 'baz'}
    >>> merge(d, {1: 'Foo', 2: 'Bar'})
    >>> items = d.items(); items.sort(); items
    [(1, 'Foo'), (2, 'Bar'), (3, 'baz')]

    :param dict1: the dictionary to merge into
    :param dict2: the dictionary containing the data that should be merged
    """
    for key, val2 in dict2.items():
        if val2 is not None:
            val1 = dict1.get(key)
            if isinstance(val2, dict):
                if val1 is None:
                    val1 = {}
                if isinstance(val1, Alias):
                    val1 = (val1, val2)
                elif isinstance(val1, tuple):
                    alias, others = val1
                    others = others.copy()
                    merge(others, val2)
                    val1 = (alias, others)
                else:
                    val1 = val1.copy()
                    merge(val1, val2)
            else:
                val1 = val2
            dict1[key] = val1


class Alias(object):
    """Representation of an alias in the locale data.

    An alias is a value that refers to some other part of the locale data,
    as specified by the `keys`.
    """

    def __init__(self, keys):
        self.keys = tuple(keys)

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.keys)

    def resolve(self, data):
        """Resolve the alias based on the given data.

        This is done recursively, so if one alias resolves to a second alias,
        that second alias will also be resolved.

        :param data: the locale data
        :type data: `dict`
        """
        base = data
        for key in self.keys:
            data = data[key]
        if isinstance(data, Alias):
            data = data.resolve(base)
        elif isinstance(data, tuple):
            alias, others = data
            data = alias.resolve(base)
        return data


class LocaleDataDict(MutableMapping):
    """Dictionary wrapper that automatically resolves aliases to the actual
    values.
    """

    def __init__(self, data, base=None):
        self._data = data
        if base is None:
            base = data
        self.base = base

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, key):
        orig = val = self._data[key]
        if isinstance(val, Alias): # resolve an alias
            val = val.resolve(self.base)
        if isinstance(val, tuple): # Merge a partial dict with an alias
            alias, others = val
            val = alias.resolve(self.base).copy()
            merge(val, others)
        if type(val) is dict: # Return a nested alias-resolving dict
            val = LocaleDataDict(val, base=self.base)
        if val is not orig:
            self._data[key] = val
        return val

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def copy(self):
        return LocaleDataDict(self._data.copy(), base=self.base)

########NEW FILE########
__FILENAME__ = _unix
from __future__ import with_statement
import os
import re
import sys
import pytz
import subprocess

_systemconfig_tz = re.compile(r'^Time Zone: (.*)$(?m)')


def _tz_from_env(tzenv):
    if tzenv[0] == ':':
        tzenv = tzenv[1:]

    # TZ specifies a file
    if os.path.exists(tzenv):
        with open(tzenv, 'rb') as tzfile:
            return pytz.tzfile.build_tzinfo('local', tzfile)

    # TZ specifies a zoneinfo zone.
    try:
        tz = pytz.timezone(tzenv)
        # That worked, so we return this:
        return tz
    except pytz.UnknownTimeZoneError:
        raise pytz.UnknownTimeZoneError(
            "tzlocal() does not support non-zoneinfo timezones like %s. \n"
            "Please use a timezone in the form of Continent/City")

def _get_localzone(_root='/'):
    """Tries to find the local timezone configuration.
    This method prefers finding the timezone name and passing that to pytz,
    over passing in the localtime file, as in the later case the zoneinfo
    name is unknown.
    The parameter _root makes the function look for files like /etc/localtime
    beneath the _root directory. This is primarily used by the tests.
    In normal usage you call the function without parameters.
    """

    tzenv = os.environ.get('TZ')
    if tzenv:
        return _tz_from_env(tzenv)

    # This is actually a pretty reliable way to test for the local time
    # zone on operating systems like OS X.  On OS X especially this is the
    # only one that actually works.
    try:
        link_dst = os.readlink('/etc/localtime')
    except OSError:
        pass
    else:
        pos = link_dst.find('/zoneinfo/')
        if pos >= 0:
            zone_name = link_dst[pos + 10:]
            try:
                return pytz.timezone(zone_name)
            except pytz.UnknownTimeZoneError:
                pass

    # If we are on OS X now we are pretty sure that the rest of the
    # code will fail and just fall through until it hits the reading
    # of /etc/localtime and using it without name.  At this point we
    # can invoke systemconfig which internally invokes ICU.  ICU itself
    # does the same thing we do (readlink + compare file contents) but
    # since it knows where the zone files are that should be a bit
    # better than reimplementing the logic here.
    if sys.platform == 'darwin':
        c = subprocess.Popen(['systemsetup', '-gettimezone'],
                             stdout=subprocess.PIPE)
        sys_result = c.communicate()[0]
        c.wait()
        tz_match = _systemconfig_tz.search(sys_result)
        if tz_match is not None:
            zone_name = tz_match.group(1)
            try:
                return pytz.timezone(zone_name)
            except pytz.UnknownTimeZoneError:
                pass

    # Now look for distribution specific configuration files
    # that contain the timezone name.
    tzpath = os.path.join(_root, 'etc/timezone')
    if os.path.exists(tzpath):
        with open(tzpath, 'rb') as tzfile:
            data = tzfile.read()

            # Issue #3 in tzlocal was that /etc/timezone was a zoneinfo file.
            # That's a misconfiguration, but we need to handle it gracefully:
            if data[:5] != 'TZif2':
                etctz = data.strip().decode()
                # Get rid of host definitions and comments:
                if ' ' in etctz:
                    etctz, dummy = etctz.split(' ', 1)
                if '#' in etctz:
                    etctz, dummy = etctz.split('#', 1)
                return pytz.timezone(etctz.replace(' ', '_'))

    # CentOS has a ZONE setting in /etc/sysconfig/clock,
    # OpenSUSE has a TIMEZONE setting in /etc/sysconfig/clock and
    # Gentoo has a TIMEZONE setting in /etc/conf.d/clock
    # We look through these files for a timezone:
    zone_re = re.compile('\s*ZONE\s*=\s*\"')
    timezone_re = re.compile('\s*TIMEZONE\s*=\s*\"')
    end_re = re.compile('\"')

    for filename in ('etc/sysconfig/clock', 'etc/conf.d/clock'):
        tzpath = os.path.join(_root, filename)
        if not os.path.exists(tzpath):
            continue
        with open(tzpath, 'rt') as tzfile:
            data = tzfile.readlines()

        for line in data:
            # Look for the ZONE= setting.
            match = zone_re.match(line)
            if match is None:
                # No ZONE= setting. Look for the TIMEZONE= setting.
                match = timezone_re.match(line)
            if match is not None:
                # Some setting existed
                line = line[match.end():]
                etctz = line[:end_re.search(line).start()]

                # We found a timezone
                return pytz.timezone(etctz.replace(' ', '_'))

    # No explicit setting existed. Use localtime
    for filename in ('etc/localtime', 'usr/local/etc/localtime'):
        tzpath = os.path.join(_root, filename)

        if not os.path.exists(tzpath):
            continue

        with open(tzpath, 'rb') as tzfile:
            return pytz.tzfile.build_tzinfo('local', tzfile)

    raise pytz.UnknownTimeZoneError('Can not find any timezone configuration')

########NEW FILE########
__FILENAME__ = _win32
try:
    import _winreg as winreg
except ImportError:
    try:
        import winreg
    except ImportError:
        winreg = None

from babel.core import get_global
import pytz


# When building the cldr data on windows this module gets imported.
# Because at that point there is no global.dat yet this call will
# fail.  We want to catch it down in that case then and just assume
# the mapping was empty.
try:
    tz_names = get_global('windows_zone_mapping')
except RuntimeError:
    tz_names = {}


def valuestodict(key):
    """Convert a registry key's values to a dictionary."""
    dict = {}
    size = winreg.QueryInfoKey(key)[1]
    for i in range(size):
        data = winreg.EnumValue(key, i)
        dict[data[0]] = data[1]
    return dict


def get_localzone_name():
    # Windows is special. It has unique time zone names (in several
    # meanings of the word) available, but unfortunately, they can be
    # translated to the language of the operating system, so we need to
    # do a backwards lookup, by going through all time zones and see which
    # one matches.
    handle = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)

    TZLOCALKEYNAME = r'SYSTEM\CurrentControlSet\Control\TimeZoneInformation'
    localtz = winreg.OpenKey(handle, TZLOCALKEYNAME)
    keyvalues = valuestodict(localtz)
    localtz.Close()
    if 'TimeZoneKeyName' in keyvalues:
        # Windows 7 (and Vista?)

        # For some reason this returns a string with loads of NUL bytes at
        # least on some systems. I don't know if this is a bug somewhere, I
        # just work around it.
        tzkeyname = keyvalues['TimeZoneKeyName'].split('\x00', 1)[0]
    else:
        # Windows 2000 or XP

        # This is the localized name:
        tzwin = keyvalues['StandardName']

        # Open the list of timezones to look up the real name:
        TZKEYNAME = r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones'
        tzkey = winreg.OpenKey(handle, TZKEYNAME)

        # Now, match this value to Time Zone information
        tzkeyname = None
        for i in range(winreg.QueryInfoKey(tzkey)[0]):
            subkey = winreg.EnumKey(tzkey, i)
            sub = winreg.OpenKey(tzkey, subkey)
            data = valuestodict(sub)
            sub.Close()
            if data['Std'] == tzwin:
                tzkeyname = subkey
                break

        tzkey.Close()
        handle.Close()

    if tzkeyname is None:
        raise LookupError('Can not find Windows timezone configuration')

    timezone = tz_names.get(tzkeyname)
    if timezone is None:
        # Nope, that didn't work. Try adding 'Standard Time',
        # it seems to work a lot of times:
        timezone = tz_names.get(tzkeyname + ' Standard Time')

    # Return what we have.
    if timezone is None:
        raise pytz.UnknownTimeZoneError('Can not find timezone ' + tzkeyname)

    return timezone


def _get_localzone():
    if winreg is None:
        raise pytz.UnknownTimeZoneError(
            'Runtime support not available')
    return pytz.timezone(get_localzone_name())

########NEW FILE########
__FILENAME__ = catalog
# -*- coding: utf-8 -*-
"""
    babel.messages.catalog
    ~~~~~~~~~~~~~~~~~~~~~~

    Data structures for message catalogs.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import re
import time

from cgi import parse_header
from datetime import datetime, time as time_
from difflib import get_close_matches
from email import message_from_string
from copy import copy

from babel import __version__ as VERSION
from babel.core import Locale
from babel.dates import format_datetime
from babel.messages.plurals import get_plural
from babel.util import odict, distinct, LOCALTZ, FixedOffsetTimezone
from babel._compat import string_types, number_types, PY2, cmp

__all__ = ['Message', 'Catalog', 'TranslationError']


PYTHON_FORMAT = re.compile(r'''(?x)
    \%
        (?:\(([\w]*)\))?
        (
            [-#0\ +]?(?:\*|[\d]+)?
            (?:\.(?:\*|[\d]+))?
            [hlL]?
        )
        ([diouxXeEfFgGcrs%])
''')


def _parse_datetime_header(value):
    match = re.match(r'^(?P<datetime>.*?)(?P<tzoffset>[+-]\d{4})?$', value)

    tt = time.strptime(match.group('datetime'), '%Y-%m-%d %H:%M')
    ts = time.mktime(tt)
    dt = datetime.fromtimestamp(ts)

    # Separate the offset into a sign component, hours, and # minutes
    tzoffset = match.group('tzoffset')
    if tzoffset is not None:
        plus_minus_s, rest = tzoffset[0], tzoffset[1:]
        hours_offset_s, mins_offset_s = rest[:2], rest[2:]

        # Make them all integers
        plus_minus = int(plus_minus_s + '1')
        hours_offset = int(hours_offset_s)
        mins_offset = int(mins_offset_s)

        # Calculate net offset
        net_mins_offset = hours_offset * 60
        net_mins_offset += mins_offset
        net_mins_offset *= plus_minus

        # Create an offset object
        tzoffset = FixedOffsetTimezone(net_mins_offset)

        # Store the offset in a datetime object
        dt = dt.replace(tzinfo=tzoffset)

    return dt


class Message(object):
    """Representation of a single message in a catalog."""

    def __init__(self, id, string=u'', locations=(), flags=(), auto_comments=(),
                 user_comments=(), previous_id=(), lineno=None, context=None):
        """Create the message object.

        :param id: the message ID, or a ``(singular, plural)`` tuple for
                   pluralizable messages
        :param string: the translated message string, or a
                       ``(singular, plural)`` tuple for pluralizable messages
        :param locations: a sequence of ``(filenname, lineno)`` tuples
        :param flags: a set or sequence of flags
        :param auto_comments: a sequence of automatic comments for the message
        :param user_comments: a sequence of user comments for the message
        :param previous_id: the previous message ID, or a ``(singular, plural)``
                            tuple for pluralizable messages
        :param lineno: the line number on which the msgid line was found in the
                       PO file, if any
        :param context: the message context
        """
        self.id = id #: The message ID
        if not string and self.pluralizable:
            string = (u'', u'')
        self.string = string #: The message translation
        self.locations = list(distinct(locations))
        self.flags = set(flags)
        if id and self.python_format:
            self.flags.add('python-format')
        else:
            self.flags.discard('python-format')
        self.auto_comments = list(distinct(auto_comments))
        self.user_comments = list(distinct(user_comments))
        if isinstance(previous_id, string_types):
            self.previous_id = [previous_id]
        else:
            self.previous_id = list(previous_id)
        self.lineno = lineno
        self.context = context

    def __repr__(self):
        return '<%s %r (flags: %r)>' % (type(self).__name__, self.id,
                                        list(self.flags))

    def __cmp__(self, obj):
        """Compare Messages, taking into account plural ids"""
        def values_to_compare():
            if isinstance(obj, Message):
                plural = self.pluralizable
                obj_plural = obj.pluralizable
                if plural and obj_plural:
                    return self.id[0], obj.id[0]
                elif plural:
                    return self.id[0], obj.id
                elif obj_plural:
                    return self.id, obj.id[0]
            return self.id, obj.id
        this, other = values_to_compare()
        return cmp(this, other)

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __ne__(self, other):
        return self.__cmp__(other) != 0

    def clone(self):
        return Message(*map(copy, (self.id, self.string, self.locations,
                                   self.flags, self.auto_comments,
                                   self.user_comments, self.previous_id,
                                   self.lineno, self.context)))

    def check(self, catalog=None):
        """Run various validation checks on the message.  Some validations
        are only performed if the catalog is provided.  This method returns
        a sequence of `TranslationError` objects.

        :rtype: ``iterator``
        :param catalog: A catalog instance that is passed to the checkers
        :see: `Catalog.check` for a way to perform checks for all messages
              in a catalog.
        """
        from babel.messages.checkers import checkers
        errors = []
        for checker in checkers:
            try:
                checker(catalog, self)
            except TranslationError as e:
                errors.append(e)
        return errors

    @property
    def fuzzy(self):
        """Whether the translation is fuzzy.

        >>> Message('foo').fuzzy
        False
        >>> msg = Message('foo', 'foo', flags=['fuzzy'])
        >>> msg.fuzzy
        True
        >>> msg
        <Message 'foo' (flags: ['fuzzy'])>

        :type:  `bool`"""
        return 'fuzzy' in self.flags

    @property
    def pluralizable(self):
        """Whether the message is plurizable.

        >>> Message('foo').pluralizable
        False
        >>> Message(('foo', 'bar')).pluralizable
        True

        :type:  `bool`"""
        return isinstance(self.id, (list, tuple))

    @property
    def python_format(self):
        """Whether the message contains Python-style parameters.

        >>> Message('foo %(name)s bar').python_format
        True
        >>> Message(('foo %(name)s', 'foo %(name)s')).python_format
        True

        :type:  `bool`"""
        ids = self.id
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        return any(PYTHON_FORMAT.search(id) for id in ids)


class TranslationError(Exception):
    """Exception thrown by translation checkers when invalid message
    translations are encountered."""


DEFAULT_HEADER = u"""\
# Translations template for PROJECT.
# Copyright (C) YEAR ORGANIZATION
# This file is distributed under the same license as the PROJECT project.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#"""


if PY2:
    def _parse_header(header_string):
        # message_from_string only works for str, not for unicode
        headers = message_from_string(header_string.encode('utf8'))
        decoded_headers = {}
        for name, value in headers.items():
            name = name.decode('utf8')
            value = value.decode('utf8')
            decoded_headers[name] = value
        return decoded_headers

else:
    _parse_header = message_from_string


class Catalog(object):
    """Representation of a message catalog."""

    def __init__(self, locale=None, domain=None, header_comment=DEFAULT_HEADER,
                 project=None, version=None, copyright_holder=None,
                 msgid_bugs_address=None, creation_date=None,
                 revision_date=None, last_translator=None, language_team=None,
                 charset=None, fuzzy=True):
        """Initialize the catalog object.

        :param locale: the locale identifier or `Locale` object, or `None`
                       if the catalog is not bound to a locale (which basically
                       means it's a template)
        :param domain: the message domain
        :param header_comment: the header comment as string, or `None` for the
                               default header
        :param project: the project's name
        :param version: the project's version
        :param copyright_holder: the copyright holder of the catalog
        :param msgid_bugs_address: the email address or URL to submit bug
                                   reports to
        :param creation_date: the date the catalog was created
        :param revision_date: the date the catalog was revised
        :param last_translator: the name and email of the last translator
        :param language_team: the name and email of the language team
        :param charset: the encoding to use in the output (defaults to utf-8)
        :param fuzzy: the fuzzy bit on the catalog header
        """
        self.domain = domain #: The message domain
        if locale:
            locale = Locale.parse(locale)
        self.locale = locale #: The locale or `None`
        self._header_comment = header_comment
        self._messages = odict()

        self.project = project or 'PROJECT' #: The project name
        self.version = version or 'VERSION' #: The project version
        self.copyright_holder = copyright_holder or 'ORGANIZATION'
        self.msgid_bugs_address = msgid_bugs_address or 'EMAIL@ADDRESS'

        self.last_translator = last_translator or 'FULL NAME <EMAIL@ADDRESS>'
        """Name and email address of the last translator."""
        self.language_team = language_team or 'LANGUAGE <LL@li.org>'
        """Name and email address of the language team."""

        self.charset = charset or 'utf-8'

        if creation_date is None:
            creation_date = datetime.now(LOCALTZ)
        elif isinstance(creation_date, datetime) and not creation_date.tzinfo:
            creation_date = creation_date.replace(tzinfo=LOCALTZ)
        self.creation_date = creation_date #: Creation date of the template
        if revision_date is None:
            revision_date = 'YEAR-MO-DA HO:MI+ZONE'
        elif isinstance(revision_date, datetime) and not revision_date.tzinfo:
            revision_date = revision_date.replace(tzinfo=LOCALTZ)
        self.revision_date = revision_date #: Last revision date of the catalog
        self.fuzzy = fuzzy #: Catalog header fuzzy bit (`True` or `False`)

        self.obsolete = odict() #: Dictionary of obsolete messages
        self._num_plurals = None
        self._plural_expr = None

    def _get_header_comment(self):
        comment = self._header_comment
        year = datetime.now(LOCALTZ).strftime('%Y')
        if hasattr(self.revision_date, 'strftime'):
            year = self.revision_date.strftime('%Y')
        comment = comment.replace('PROJECT', self.project) \
                         .replace('VERSION', self.version) \
                         .replace('YEAR', year) \
                         .replace('ORGANIZATION', self.copyright_holder)
        if self.locale:
            comment = comment.replace('Translations template', '%s translations'
                                      % self.locale.english_name)
        return comment

    def _set_header_comment(self, string):
        self._header_comment = string

    header_comment = property(_get_header_comment, _set_header_comment, doc="""\
    The header comment for the catalog.

    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   copyright_holder='Foo Company')
    >>> print catalog.header_comment #doctest: +ELLIPSIS
    # Translations template for Foobar.
    # Copyright (C) ... Foo Company
    # This file is distributed under the same license as the Foobar project.
    # FIRST AUTHOR <EMAIL@ADDRESS>, ....
    #

    The header can also be set from a string. Any known upper-case variables
    will be replaced when the header is retrieved again:

    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   copyright_holder='Foo Company')
    >>> catalog.header_comment = '''\\
    ... # The POT for my really cool PROJECT project.
    ... # Copyright (C) 1990-2003 ORGANIZATION
    ... # This file is distributed under the same license as the PROJECT
    ... # project.
    ... #'''
    >>> print catalog.header_comment
    # The POT for my really cool Foobar project.
    # Copyright (C) 1990-2003 Foo Company
    # This file is distributed under the same license as the Foobar
    # project.
    #

    :type: `unicode`
    """)

    def _get_mime_headers(self):
        headers = []
        headers.append(('Project-Id-Version',
                        '%s %s' % (self.project, self.version)))
        headers.append(('Report-Msgid-Bugs-To', self.msgid_bugs_address))
        headers.append(('POT-Creation-Date',
                        format_datetime(self.creation_date, 'yyyy-MM-dd HH:mmZ',
                                        locale='en')))
        if isinstance(self.revision_date, (datetime, time_) + number_types):
            headers.append(('PO-Revision-Date',
                            format_datetime(self.revision_date,
                                            'yyyy-MM-dd HH:mmZ', locale='en')))
        else:
            headers.append(('PO-Revision-Date', self.revision_date))
        headers.append(('Last-Translator', self.last_translator))
        if (self.locale is not None) and ('LANGUAGE' in self.language_team):
            headers.append(('Language-Team',
                           self.language_team.replace('LANGUAGE',
                                                      str(self.locale))))
        else:
            headers.append(('Language-Team', self.language_team))
        if self.locale is not None:
            headers.append(('Plural-Forms', self.plural_forms))
        headers.append(('MIME-Version', '1.0'))
        headers.append(('Content-Type',
                        'text/plain; charset=%s' % self.charset))
        headers.append(('Content-Transfer-Encoding', '8bit'))
        headers.append(('Generated-By', 'Babel %s\n' % VERSION))
        return headers

    def _set_mime_headers(self, headers):
        for name, value in headers:
            name = name.lower()
            if name == 'project-id-version':
                parts = value.split(' ')
                self.project = u' '.join(parts[:-1])
                self.version = parts[-1]
            elif name == 'report-msgid-bugs-to':
                self.msgid_bugs_address = value
            elif name == 'last-translator':
                self.last_translator = value
            elif name == 'language-team':
                self.language_team = value
            elif name == 'content-type':
                mimetype, params = parse_header(value)
                if 'charset' in params:
                    self.charset = params['charset'].lower()
            elif name == 'plural-forms':
                _, params = parse_header(' ;' + value)
                self._num_plurals = int(params.get('nplurals', 2))
                self._plural_expr = params.get('plural', '(n != 1)')
            elif name == 'pot-creation-date':
                self.creation_date = _parse_datetime_header(value)
            elif name == 'po-revision-date':
                # Keep the value if it's not the default one
                if 'YEAR' not in value:
                    self.revision_date = _parse_datetime_header(value)

    mime_headers = property(_get_mime_headers, _set_mime_headers, doc="""\
    The MIME headers of the catalog, used for the special ``msgid ""`` entry.

    The behavior of this property changes slightly depending on whether a locale
    is set or not, the latter indicating that the catalog is actually a template
    for actual translations.

    Here's an example of the output for such a catalog template:

    >>> from babel.dates import UTC
    >>> created = datetime(1990, 4, 1, 15, 30, tzinfo=UTC)
    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   creation_date=created)
    >>> for name, value in catalog.mime_headers:
    ...     print '%s: %s' % (name, value)
    Project-Id-Version: Foobar 1.0
    Report-Msgid-Bugs-To: EMAIL@ADDRESS
    POT-Creation-Date: 1990-04-01 15:30+0000
    PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
    Last-Translator: FULL NAME <EMAIL@ADDRESS>
    Language-Team: LANGUAGE <LL@li.org>
    MIME-Version: 1.0
    Content-Type: text/plain; charset=utf-8
    Content-Transfer-Encoding: 8bit
    Generated-By: Babel ...

    And here's an example of the output when the locale is set:

    >>> revised = datetime(1990, 8, 3, 12, 0, tzinfo=UTC)
    >>> catalog = Catalog(locale='de_DE', project='Foobar', version='1.0',
    ...                   creation_date=created, revision_date=revised,
    ...                   last_translator='John Doe <jd@example.com>',
    ...                   language_team='de_DE <de@example.com>')
    >>> for name, value in catalog.mime_headers:
    ...     print '%s: %s' % (name, value)
    Project-Id-Version: Foobar 1.0
    Report-Msgid-Bugs-To: EMAIL@ADDRESS
    POT-Creation-Date: 1990-04-01 15:30+0000
    PO-Revision-Date: 1990-08-03 12:00+0000
    Last-Translator: John Doe <jd@example.com>
    Language-Team: de_DE <de@example.com>
    Plural-Forms: nplurals=2; plural=(n != 1)
    MIME-Version: 1.0
    Content-Type: text/plain; charset=utf-8
    Content-Transfer-Encoding: 8bit
    Generated-By: Babel ...

    :type: `list`
    """)

    @property
    def num_plurals(self):
        """The number of plurals used by the catalog or locale.

        >>> Catalog(locale='en').num_plurals
        2
        >>> Catalog(locale='ga').num_plurals
        3

        :type: `int`"""
        if self._num_plurals is None:
            num = 2
            if self.locale:
                num = get_plural(self.locale)[0]
            self._num_plurals = num
        return self._num_plurals

    @property
    def plural_expr(self):
        """The plural expression used by the catalog or locale.

        >>> Catalog(locale='en').plural_expr
        '(n != 1)'
        >>> Catalog(locale='ga').plural_expr
        '(n==1 ? 0 : n==2 ? 1 : 2)'

        :type: `string_types`"""
        if self._plural_expr is None:
            expr = '(n != 1)'
            if self.locale:
                expr = get_plural(self.locale)[1]
            self._plural_expr = expr
        return self._plural_expr

    @property
    def plural_forms(self):
        """Return the plural forms declaration for the locale.

        >>> Catalog(locale='en').plural_forms
        'nplurals=2; plural=(n != 1)'
        >>> Catalog(locale='pt_BR').plural_forms
        'nplurals=2; plural=(n > 1)'

        :type: `str`"""
        return 'nplurals=%s; plural=%s' % (self.num_plurals, self.plural_expr)

    def __contains__(self, id):
        """Return whether the catalog has a message with the specified ID."""
        return self._key_for(id) in self._messages

    def __len__(self):
        """The number of messages in the catalog.

        This does not include the special ``msgid ""`` entry."""
        return len(self._messages)

    def __iter__(self):
        """Iterates through all the entries in the catalog, in the order they
        were added, yielding a `Message` object for every entry.

        :rtype: ``iterator``"""
        buf = []
        for name, value in self.mime_headers:
            buf.append('%s: %s' % (name, value))
        flags = set()
        if self.fuzzy:
            flags |= set(['fuzzy'])
        yield Message(u'', '\n'.join(buf), flags=flags)
        for key in self._messages:
            yield self._messages[key]

    def __repr__(self):
        locale = ''
        if self.locale:
            locale = ' %s' % self.locale
        return '<%s %r%s>' % (type(self).__name__, self.domain, locale)

    def __delitem__(self, id):
        """Delete the message with the specified ID."""
        self.delete(id)

    def __getitem__(self, id):
        """Return the message with the specified ID.

        :param id: the message ID
        """
        return self.get(id)

    def __setitem__(self, id, message):
        """Add or update the message with the specified ID.

        >>> catalog = Catalog()
        >>> catalog[u'foo'] = Message(u'foo')
        >>> catalog[u'foo']
        <Message u'foo' (flags: [])>

        If a message with that ID is already in the catalog, it is updated
        to include the locations and flags of the new message.

        >>> catalog = Catalog()
        >>> catalog[u'foo'] = Message(u'foo', locations=[('main.py', 1)])
        >>> catalog[u'foo'].locations
        [('main.py', 1)]
        >>> catalog[u'foo'] = Message(u'foo', locations=[('utils.py', 5)])
        >>> catalog[u'foo'].locations
        [('main.py', 1), ('utils.py', 5)]

        :param id: the message ID
        :param message: the `Message` object
        """
        assert isinstance(message, Message), 'expected a Message object'
        key = self._key_for(id, message.context)
        current = self._messages.get(key)
        if current:
            if message.pluralizable and not current.pluralizable:
                # The new message adds pluralization
                current.id = message.id
                current.string = message.string
            current.locations = list(distinct(current.locations +
                                              message.locations))
            current.auto_comments = list(distinct(current.auto_comments +
                                                  message.auto_comments))
            current.user_comments = list(distinct(current.user_comments +
                                                  message.user_comments))
            current.flags |= message.flags
            message = current
        elif id == '':
            # special treatment for the header message
            self.mime_headers = _parse_header(message.string).items()
            self.header_comment = '\n'.join([('# %s' % c).rstrip() for c
                                             in message.user_comments])
            self.fuzzy = message.fuzzy
        else:
            if isinstance(id, (list, tuple)):
                assert isinstance(message.string, (list, tuple)), \
                    'Expected sequence but got %s' % type(message.string)
            self._messages[key] = message

    def add(self, id, string=None, locations=(), flags=(), auto_comments=(),
            user_comments=(), previous_id=(), lineno=None, context=None):
        """Add or update the message with the specified ID.

        >>> catalog = Catalog()
        >>> catalog.add(u'foo')
        <Message ...>
        >>> catalog[u'foo']
        <Message u'foo' (flags: [])>

        This method simply constructs a `Message` object with the given
        arguments and invokes `__setitem__` with that object.

        :param id: the message ID, or a ``(singular, plural)`` tuple for
                   pluralizable messages
        :param string: the translated message string, or a
                       ``(singular, plural)`` tuple for pluralizable messages
        :param locations: a sequence of ``(filenname, lineno)`` tuples
        :param flags: a set or sequence of flags
        :param auto_comments: a sequence of automatic comments
        :param user_comments: a sequence of user comments
        :param previous_id: the previous message ID, or a ``(singular, plural)``
                            tuple for pluralizable messages
        :param lineno: the line number on which the msgid line was found in the
                       PO file, if any
        :param context: the message context
        """
        message = Message(id, string, list(locations), flags, auto_comments,
                          user_comments, previous_id, lineno=lineno,
                          context=context)
        self[id] = message
        return message

    def check(self):
        """Run various validation checks on the translations in the catalog.

        For every message which fails validation, this method yield a
        ``(message, errors)`` tuple, where ``message`` is the `Message` object
        and ``errors`` is a sequence of `TranslationError` objects.

        :rtype: ``iterator``
        """
        for message in self._messages.values():
            errors = message.check(catalog=self)
            if errors:
                yield message, errors

    def get(self, id, context=None):
        """Return the message with the specified ID and context.

        :param id: the message ID
        :param context: the message context, or ``None`` for no context
        """
        return self._messages.get(self._key_for(id, context))

    def delete(self, id, context=None):
        """Delete the message with the specified ID and context.

        :param id: the message ID
        :param context: the message context, or ``None`` for no context
        """
        key = self._key_for(id, context)
        if key in self._messages:
            del self._messages[key]

    def update(self, template, no_fuzzy_matching=False):
        """Update the catalog based on the given template catalog.

        >>> from babel.messages import Catalog
        >>> template = Catalog()
        >>> template.add('green', locations=[('main.py', 99)])
        <Message ...>
        >>> template.add('blue', locations=[('main.py', 100)])
        <Message ...>
        >>> template.add(('salad', 'salads'), locations=[('util.py', 42)])
        <Message ...>
        >>> catalog = Catalog(locale='de_DE')
        >>> catalog.add('blue', u'blau', locations=[('main.py', 98)])
        <Message ...>
        >>> catalog.add('head', u'Kopf', locations=[('util.py', 33)])
        <Message ...>
        >>> catalog.add(('salad', 'salads'), (u'Salat', u'Salate'),
        ...             locations=[('util.py', 38)])
        <Message ...>

        >>> catalog.update(template)
        >>> len(catalog)
        3

        >>> msg1 = catalog['green']
        >>> msg1.string
        >>> msg1.locations
        [('main.py', 99)]

        >>> msg2 = catalog['blue']
        >>> msg2.string
        u'blau'
        >>> msg2.locations
        [('main.py', 100)]

        >>> msg3 = catalog['salad']
        >>> msg3.string
        (u'Salat', u'Salate')
        >>> msg3.locations
        [('util.py', 42)]

        Messages that are in the catalog but not in the template are removed
        from the main collection, but can still be accessed via the `obsolete`
        member:

        >>> 'head' in catalog
        False
        >>> catalog.obsolete.values()
        [<Message 'head' (flags: [])>]

        :param template: the reference catalog, usually read from a POT file
        :param no_fuzzy_matching: whether to use fuzzy matching of message IDs
        """
        messages = self._messages
        remaining = messages.copy()
        self._messages = odict()

        # Prepare for fuzzy matching
        fuzzy_candidates = []
        if not no_fuzzy_matching:
            fuzzy_candidates = dict([
                (self._key_for(msgid), messages[msgid].context)
                for msgid in messages if msgid and messages[msgid].string
            ])
        fuzzy_matches = set()

        def _merge(message, oldkey, newkey):
            message = message.clone()
            fuzzy = False
            if oldkey != newkey:
                fuzzy = True
                fuzzy_matches.add(oldkey)
                oldmsg = messages.get(oldkey)
                if isinstance(oldmsg.id, string_types):
                    message.previous_id = [oldmsg.id]
                else:
                    message.previous_id = list(oldmsg.id)
            else:
                oldmsg = remaining.pop(oldkey, None)
            message.string = oldmsg.string
            if isinstance(message.id, (list, tuple)):
                if not isinstance(message.string, (list, tuple)):
                    fuzzy = True
                    message.string = tuple(
                        [message.string] + ([u''] * (len(message.id) - 1))
                    )
                elif len(message.string) != self.num_plurals:
                    fuzzy = True
                    message.string = tuple(message.string[:len(oldmsg.string)])
            elif isinstance(message.string, (list, tuple)):
                fuzzy = True
                message.string = message.string[0]
            message.flags |= oldmsg.flags
            if fuzzy:
                message.flags |= set([u'fuzzy'])
            self[message.id] = message

        for message in template:
            if message.id:
                key = self._key_for(message.id, message.context)
                if key in messages:
                    _merge(message, key, key)
                else:
                    if no_fuzzy_matching is False:
                        # do some fuzzy matching with difflib
                        if isinstance(key, tuple):
                            matchkey = key[0] # just the msgid, no context
                        else:
                            matchkey = key
                        matches = get_close_matches(matchkey.lower().strip(),
                                                    fuzzy_candidates.keys(), 1)
                        if matches:
                            newkey = matches[0]
                            newctxt = fuzzy_candidates[newkey]
                            if newctxt is not None:
                                newkey = newkey, newctxt
                            _merge(message, newkey, key)
                            continue

                    self[message.id] = message

        for msgid in remaining:
            if no_fuzzy_matching or msgid not in fuzzy_matches:
                self.obsolete[msgid] = remaining[msgid]
        # Make updated catalog's POT-Creation-Date equal to the template
        # used to update the catalog
        self.creation_date = template.creation_date

    def _key_for(self, id, context=None):
        """The key for a message is just the singular ID even for pluralizable
        messages, but is a ``(msgid, msgctxt)`` tuple for context-specific
        messages.
        """
        key = id
        if isinstance(key, (list, tuple)):
            key = id[0]
        if context is not None:
            key = (key, context)
        return key

########NEW FILE########
__FILENAME__ = checkers
# -*- coding: utf-8 -*-
"""
    babel.messages.checkers
    ~~~~~~~~~~~~~~~~~~~~~~~

    Various routines that help with validation of translations.

    :since: version 0.9

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

from babel.messages.catalog import TranslationError, PYTHON_FORMAT
from babel._compat import string_types, izip


#: list of format chars that are compatible to each other
_string_format_compatibilities = [
    set(['i', 'd', 'u']),
    set(['x', 'X']),
    set(['f', 'F', 'g', 'G'])
]


def num_plurals(catalog, message):
    """Verify the number of plurals in the translation."""
    if not message.pluralizable:
        if not isinstance(message.string, string_types):
            raise TranslationError("Found plural forms for non-pluralizable "
                                   "message")
        return

    # skip further tests if no catalog is provided.
    elif catalog is None:
        return

    msgstrs = message.string
    if not isinstance(msgstrs, (list, tuple)):
        msgstrs = (msgstrs,)
    if len(msgstrs) != catalog.num_plurals:
        raise TranslationError("Wrong number of plural forms (expected %d)" %
                               catalog.num_plurals)


def python_format(catalog, message):
    """Verify the format string placeholders in the translation."""
    if 'python-format' not in message.flags:
        return
    msgids = message.id
    if not isinstance(msgids, (list, tuple)):
        msgids = (msgids,)
    msgstrs = message.string
    if not isinstance(msgstrs, (list, tuple)):
        msgstrs = (msgstrs,)

    for msgid, msgstr in izip(msgids, msgstrs):
        if msgstr:
            _validate_format(msgid, msgstr)


def _validate_format(format, alternative):
    """Test format string `alternative` against `format`.  `format` can be the
    msgid of a message and `alternative` one of the `msgstr`\s.  The two
    arguments are not interchangeable as `alternative` may contain less
    placeholders if `format` uses named placeholders.

    The behavior of this function is undefined if the string does not use
    string formattings.

    If the string formatting of `alternative` is compatible to `format` the
    function returns `None`, otherwise a `TranslationError` is raised.

    Examples for compatible format strings:

    >>> _validate_format('Hello %s!', 'Hallo %s!')
    >>> _validate_format('Hello %i!', 'Hallo %d!')

    Example for an incompatible format strings:

    >>> _validate_format('Hello %(name)s!', 'Hallo %s!')
    Traceback (most recent call last):
      ...
    TranslationError: the format strings are of different kinds

    This function is used by the `python_format` checker.

    :param format: The original format string
    :param alternative: The alternative format string that should be checked
                        against format
    :raises TranslationError: on formatting errors
    """

    def _parse(string):
        result = []
        for match in PYTHON_FORMAT.finditer(string):
            name, format, typechar = match.groups()
            if typechar == '%' and name is None:
                continue
            result.append((name, str(typechar)))
        return result

    def _compatible(a, b):
        if a == b:
            return True
        for set in _string_format_compatibilities:
            if a in set and b in set:
                return True
        return False

    def _check_positional(results):
        positional = None
        for name, char in results:
            if positional is None:
                positional = name is None
            else:
                if (name is None) != positional:
                    raise TranslationError('format string mixes positional '
                                           'and named placeholders')
        return bool(positional)

    a, b = map(_parse, (format, alternative))

    # now check if both strings are positional or named
    a_positional, b_positional = map(_check_positional, (a, b))
    if a_positional and not b_positional and not b:
        raise TranslationError('placeholders are incompatible')
    elif a_positional != b_positional:
        raise TranslationError('the format strings are of different kinds')

    # if we are operating on positional strings both must have the
    # same number of format chars and those must be compatible
    if a_positional:
        if len(a) != len(b):
            raise TranslationError('positional format placeholders are '
                                   'unbalanced')
        for idx, ((_, first), (_, second)) in enumerate(izip(a, b)):
            if not _compatible(first, second):
                raise TranslationError('incompatible format for placeholder '
                                       '%d: %r and %r are not compatible' %
                                       (idx + 1, first, second))

    # otherwise the second string must not have names the first one
    # doesn't have and the types of those included must be compatible
    else:
        type_map = dict(a)
        for name, typechar in b:
            if name not in type_map:
                raise TranslationError('unknown named placeholder %r' % name)
            elif not _compatible(typechar, type_map[name]):
                raise TranslationError('incompatible format for '
                                       'placeholder %r: '
                                       '%r and %r are not compatible' %
                                       (name, typechar, type_map[name]))


def _find_checkers():
    checkers = []
    try:
        from pkg_resources import working_set
    except ImportError:
        pass
    else:
        for entry_point in working_set.iter_entry_points('babel.checkers'):
            checkers.append(entry_point.load())
    if len(checkers) == 0:
        # if pkg_resources is not available or no usable egg-info was found
        # (see #230), just resort to hard-coded checkers
        return [num_plurals, python_format]
    return checkers


checkers = _find_checkers()

########NEW FILE########
__FILENAME__ = extract
# -*- coding: utf-8 -*-
"""
    babel.messages.extract
    ~~~~~~~~~~~~~~~~~~~~~~

    Basic infrastructure for extracting localizable messages from source files.

    This module defines an extensible system for collecting localizable message
    strings from a variety of sources. A native extractor for Python source
    files is builtin, extractors for other sources can be added using very
    simple plugins.

    The main entry points into the extraction functionality are the functions
    `extract_from_dir` and `extract_from_file`.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import os
import sys
from tokenize import generate_tokens, COMMENT, NAME, OP, STRING

from babel.util import parse_encoding, pathmatch, relpath
from babel._compat import PY2, text_type
from textwrap import dedent


GROUP_NAME = 'babel.extractors'

DEFAULT_KEYWORDS = {
    '_': None,
    'gettext': None,
    'ngettext': (1, 2),
    'ugettext': None,
    'ungettext': (1, 2),
    'dgettext': (2,),
    'dngettext': (2, 3),
    'N_': None,
    'pgettext': ((1, 'c'), 2)
}

DEFAULT_MAPPING = [('**.py', 'python')]

empty_msgid_warning = (
'%s: warning: Empty msgid.  It is reserved by GNU gettext: gettext("") '
'returns the header entry with meta information, not the empty string.')


def _strip_comment_tags(comments, tags):
    """Helper function for `extract` that strips comment tags from strings
    in a list of comment lines.  This functions operates in-place.
    """
    def _strip(line):
        for tag in tags:
            if line.startswith(tag):
                return line[len(tag):].strip()
        return line
    comments[:] = map(_strip, comments)


def extract_from_dir(dirname=None, method_map=DEFAULT_MAPPING,
                     options_map=None, keywords=DEFAULT_KEYWORDS,
                     comment_tags=(), callback=None, strip_comment_tags=False):
    """Extract messages from any source files found in the given directory.

    This function generates tuples of the form ``(filename, lineno, message,
    comments, context)``.

    Which extraction method is used per file is determined by the `method_map`
    parameter, which maps extended glob patterns to extraction method names.
    For example, the following is the default mapping:

    >>> method_map = [
    ...     ('**.py', 'python')
    ... ]

    This basically says that files with the filename extension ".py" at any
    level inside the directory should be processed by the "python" extraction
    method. Files that don't match any of the mapping patterns are ignored. See
    the documentation of the `pathmatch` function for details on the pattern
    syntax.

    The following extended mapping would also use the "genshi" extraction
    method on any file in "templates" subdirectory:

    >>> method_map = [
    ...     ('**/templates/**.*', 'genshi'),
    ...     ('**.py', 'python')
    ... ]

    The dictionary provided by the optional `options_map` parameter augments
    these mappings. It uses extended glob patterns as keys, and the values are
    dictionaries mapping options names to option values (both strings).

    The glob patterns of the `options_map` do not necessarily need to be the
    same as those used in the method mapping. For example, while all files in
    the ``templates`` folders in an application may be Genshi applications, the
    options for those files may differ based on extension:

    >>> options_map = {
    ...     '**/templates/**.txt': {
    ...         'template_class': 'genshi.template:TextTemplate',
    ...         'encoding': 'latin-1'
    ...     },
    ...     '**/templates/**.html': {
    ...         'include_attrs': ''
    ...     }
    ... }

    :param dirname: the path to the directory to extract messages from.  If
                    not given the current working directory is used.
    :param method_map: a list of ``(pattern, method)`` tuples that maps of
                       extraction method names to extended glob patterns
    :param options_map: a dictionary of additional options (optional)
    :param keywords: a dictionary mapping keywords (i.e. names of functions
                     that should be recognized as translation functions) to
                     tuples that specify which of their arguments contain
                     localizable strings
    :param comment_tags: a list of tags of translator comments to search for
                         and include in the results
    :param callback: a function that is called for every file that message are
                     extracted from, just before the extraction itself is
                     performed; the function is passed the filename, the name
                     of the extraction method and and the options dictionary as
                     positional arguments, in that order
    :param strip_comment_tags: a flag that if set to `True` causes all comment
                               tags to be removed from the collected comments.
    :see: `pathmatch`
    """
    if dirname is None:
        dirname = os.getcwd()
    if options_map is None:
        options_map = {}

    absname = os.path.abspath(dirname)
    for root, dirnames, filenames in os.walk(absname):
        for subdir in dirnames:
            if subdir.startswith('.') or subdir.startswith('_'):
                dirnames.remove(subdir)
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            filename = relpath(
                os.path.join(root, filename).replace(os.sep, '/'),
                dirname
            )
            for pattern, method in method_map:
                if pathmatch(pattern, filename):
                    filepath = os.path.join(absname, filename)
                    options = {}
                    for opattern, odict in options_map.items():
                        if pathmatch(opattern, filename):
                            options = odict
                    if callback:
                        callback(filename, method, options)
                    for lineno, message, comments, context in \
                          extract_from_file(method, filepath,
                                            keywords=keywords,
                                            comment_tags=comment_tags,
                                            options=options,
                                            strip_comment_tags=
                                                strip_comment_tags):
                        yield filename, lineno, message, comments, context
                    break


def extract_from_file(method, filename, keywords=DEFAULT_KEYWORDS,
                      comment_tags=(), options=None, strip_comment_tags=False):
    """Extract messages from a specific file.

    This function returns a list of tuples of the form ``(lineno, funcname,
    message)``.

    :param filename: the path to the file to extract messages from
    :param method: a string specifying the extraction method (.e.g. "python")
    :param keywords: a dictionary mapping keywords (i.e. names of functions
                     that should be recognized as translation functions) to
                     tuples that specify which of their arguments contain
                     localizable strings
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param strip_comment_tags: a flag that if set to `True` causes all comment
                               tags to be removed from the collected comments.
    :param options: a dictionary of additional options (optional)
    """
    fileobj = open(filename, 'rb')
    try:
        return list(extract(method, fileobj, keywords, comment_tags, options,
                            strip_comment_tags))
    finally:
        fileobj.close()


def extract(method, fileobj, keywords=DEFAULT_KEYWORDS, comment_tags=(),
            options=None, strip_comment_tags=False):
    """Extract messages from the given file-like object using the specified
    extraction method.

    This function returns tuples of the form ``(lineno, message, comments)``.

    The implementation dispatches the actual extraction to plugins, based on the
    value of the ``method`` parameter.

    >>> source = '''# foo module
    ... def run(argv):
    ...    print _('Hello, world!')
    ... '''

    >>> from StringIO import StringIO
    >>> for message in extract('python', StringIO(source)):
    ...     print message
    (3, u'Hello, world!', [], None)

    :param method: a string specifying the extraction method (.e.g. "python");
                   if this is a simple name, the extraction function will be
                   looked up by entry point; if it is an explicit reference
                   to a function (of the form ``package.module:funcname`` or
                   ``package.module.funcname``), the corresponding function
                   will be imported and used
    :param fileobj: the file-like object the messages should be extracted from
    :param keywords: a dictionary mapping keywords (i.e. names of functions
                     that should be recognized as translation functions) to
                     tuples that specify which of their arguments contain
                     localizable strings
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :param strip_comment_tags: a flag that if set to `True` causes all comment
                               tags to be removed from the collected comments.
    :raise ValueError: if the extraction method is not registered
    """
    func = None
    if ':' in method or '.' in method:
        if ':' not in method:
            lastdot = method.rfind('.')
            module, attrname = method[:lastdot], method[lastdot + 1:]
        else:
            module, attrname = method.split(':', 1)
        func = getattr(__import__(module, {}, {}, [attrname]), attrname)
    else:
        try:
            from pkg_resources import working_set
        except ImportError:
            pass
        else:
            for entry_point in working_set.iter_entry_points(GROUP_NAME,
                                                             method):
                func = entry_point.load(require=True)
                break
        if func is None:
            # if pkg_resources is not available or no usable egg-info was found
            # (see #230), we resort to looking up the builtin extractors
            # directly
            builtin = {
                'ignore': extract_nothing,
                'python': extract_python,
                'javascript': extract_javascript
            }
            func = builtin.get(method)
    if func is None:
        raise ValueError('Unknown extraction method %r' % method)

    results = func(fileobj, keywords.keys(), comment_tags,
                   options=options or {})

    for lineno, funcname, messages, comments in results:
        if funcname:
            spec = keywords[funcname] or (1,)
        else:
            spec = (1,)
        if not isinstance(messages, (list, tuple)):
            messages = [messages]
        if not messages:
            continue

        # Validate the messages against the keyword's specification
        context = None
        msgs = []
        invalid = False
        # last_index is 1 based like the keyword spec
        last_index = len(messages)
        for index in spec:
            if isinstance(index, tuple):
                context = messages[index[0] - 1]
                continue
            if last_index < index:
                # Not enough arguments
                invalid = True
                break
            message = messages[index - 1]
            if message is None:
                invalid = True
                break
            msgs.append(message)
        if invalid:
            continue

        # keyword spec indexes are 1 based, therefore '-1'
        if isinstance(spec[0], tuple):
            # context-aware *gettext method
            first_msg_index = spec[1] - 1
        else:
            first_msg_index = spec[0] - 1
        if not messages[first_msg_index]:
            # An empty string msgid isn't valid, emit a warning
            where = '%s:%i' % (hasattr(fileobj, 'name') and \
                                   fileobj.name or '(unknown)', lineno)
            sys.stderr.write((empty_msgid_warning % where) + '\n')
            continue

        messages = tuple(msgs)
        if len(messages) == 1:
            messages = messages[0]

        if strip_comment_tags:
            _strip_comment_tags(comments, comment_tags)
        yield lineno, messages, comments, context


def extract_nothing(fileobj, keywords, comment_tags, options):
    """Pseudo extractor that does not actually extract anything, but simply
    returns an empty list.
    """
    return []


def extract_python(fileobj, keywords, comment_tags, options):
    """Extract messages from Python source code.

    It returns an iterator yielding tuples in the following form ``(lineno,
    funcname, message, comments)``.

    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :rtype: ``iterator``
    """
    funcname = lineno = message_lineno = None
    call_stack = -1
    buf = []
    messages = []
    translator_comments = []
    in_def = in_translator_comments = False
    comment_tag = None

    encoding = parse_encoding(fileobj) or options.get('encoding', 'iso-8859-1')

    if PY2:
        next_line = fileobj.readline
    else:
        next_line = lambda: fileobj.readline().decode(encoding)

    tokens = generate_tokens(next_line)
    for tok, value, (lineno, _), _, _ in tokens:
        if call_stack == -1 and tok == NAME and value in ('def', 'class'):
            in_def = True
        elif tok == OP and value == '(':
            if in_def:
                # Avoid false positives for declarations such as:
                # def gettext(arg='message'):
                in_def = False
                continue
            if funcname:
                message_lineno = lineno
                call_stack += 1
        elif in_def and tok == OP and value == ':':
            # End of a class definition without parens
            in_def = False
            continue
        elif call_stack == -1 and tok == COMMENT:
            # Strip the comment token from the line
            if PY2:
                value = value.decode(encoding)
            value = value[1:].strip()
            if in_translator_comments and \
                    translator_comments[-1][0] == lineno - 1:
                # We're already inside a translator comment, continue appending
                translator_comments.append((lineno, value))
                continue
            # If execution reaches this point, let's see if comment line
            # starts with one of the comment tags
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    in_translator_comments = True
                    translator_comments.append((lineno, value))
                    break
        elif funcname and call_stack == 0:
            if tok == OP and value == ')':
                if buf:
                    messages.append(''.join(buf))
                    del buf[:]
                else:
                    messages.append(None)

                if len(messages) > 1:
                    messages = tuple(messages)
                else:
                    messages = messages[0]
                # Comments don't apply unless they immediately preceed the
                # message
                if translator_comments and \
                        translator_comments[-1][0] < message_lineno - 1:
                    translator_comments = []

                yield (message_lineno, funcname, messages,
                       [comment[1] for comment in translator_comments])

                funcname = lineno = message_lineno = None
                call_stack = -1
                messages = []
                translator_comments = []
                in_translator_comments = False
            elif tok == STRING:
                # Unwrap quotes in a safe manner, maintaining the string's
                # encoding
                # https://sourceforge.net/tracker/?func=detail&atid=355470&
                # aid=617979&group_id=5470
                value = eval('# coding=%s\n%s' % (str(encoding), value),
                             {'__builtins__':{}}, {})
                if PY2 and not isinstance(value, text_type):
                    value = value.decode(encoding)
                buf.append(value)
            elif tok == OP and value == ',':
                if buf:
                    messages.append(''.join(buf))
                    del buf[:]
                else:
                    messages.append(None)
                if translator_comments:
                    # We have translator comments, and since we're on a
                    # comma(,) user is allowed to break into a new line
                    # Let's increase the last comment's lineno in order
                    # for the comment to still be a valid one
                    old_lineno, old_comment = translator_comments.pop()
                    translator_comments.append((old_lineno+1, old_comment))
        elif call_stack > 0 and tok == OP and value == ')':
            call_stack -= 1
        elif funcname and call_stack == -1:
            funcname = None
        elif tok == NAME and value in keywords:
            funcname = value


def extract_javascript(fileobj, keywords, comment_tags, options):
    """Extract messages from JavaScript source code.

    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    """
    from babel.messages.jslexer import tokenize, unquote_string
    funcname = message_lineno = None
    messages = []
    last_argument = None
    translator_comments = []
    concatenate_next = False
    encoding = options.get('encoding', 'utf-8')
    last_token = None
    call_stack = -1

    for token in tokenize(fileobj.read().decode(encoding)):
        if token.type == 'operator' and token.value == '(':
            if funcname:
                message_lineno = token.lineno
                call_stack += 1

        elif call_stack == -1 and token.type == 'linecomment':
            value = token.value[2:].strip()
            if translator_comments and \
               translator_comments[-1][0] == token.lineno - 1:
                translator_comments.append((token.lineno, value))
                continue

            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    translator_comments.append((token.lineno, value.strip()))
                    break

        elif token.type == 'multilinecomment':
            # only one multi-line comment may preceed a translation
            translator_comments = []
            value = token.value[2:-2].strip()
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    lines = value.splitlines()
                    if lines:
                        lines[0] = lines[0].strip()
                        lines[1:] = dedent('\n'.join(lines[1:])).splitlines()
                        for offset, line in enumerate(lines):
                            translator_comments.append((token.lineno + offset,
                                                        line))
                    break

        elif funcname and call_stack == 0:
            if token.type == 'operator' and token.value == ')':
                if last_argument is not None:
                    messages.append(last_argument)
                if len(messages) > 1:
                    messages = tuple(messages)
                elif messages:
                    messages = messages[0]
                else:
                    messages = None

                # Comments don't apply unless they immediately precede the
                # message
                if translator_comments and \
                   translator_comments[-1][0] < message_lineno - 1:
                    translator_comments = []

                if messages is not None:
                    yield (message_lineno, funcname, messages,
                           [comment[1] for comment in translator_comments])

                funcname = message_lineno = last_argument = None
                concatenate_next = False
                translator_comments = []
                messages = []
                call_stack = -1

            elif token.type == 'string':
                new_value = unquote_string(token.value)
                if concatenate_next:
                    last_argument = (last_argument or '') + new_value
                    concatenate_next = False
                else:
                    last_argument = new_value

            elif token.type == 'operator':
                if token.value == ',':
                    if last_argument is not None:
                        messages.append(last_argument)
                        last_argument = None
                    else:
                        messages.append(None)
                    concatenate_next = False
                elif token.value == '+':
                    concatenate_next = True

        elif call_stack > 0 and token.type == 'operator' \
             and token.value == ')':
            call_stack -= 1

        elif funcname and call_stack == -1:
            funcname = None

        elif call_stack == -1 and token.type == 'name' and \
             token.value in keywords and \
             (last_token is None or last_token.type != 'name' or
              last_token.value != 'function'):
            funcname = token.value

        last_token = token

########NEW FILE########
__FILENAME__ = frontend
# -*- coding: utf-8 -*-
"""
    babel.messages.frontend
    ~~~~~~~~~~~~~~~~~~~~~~~

    Frontends for the message extraction functionality.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

try:
    from ConfigParser import RawConfigParser
except ImportError:
    from configparser import RawConfigParser
from datetime import datetime
from distutils import log
from distutils.cmd import Command
from distutils.errors import DistutilsOptionError, DistutilsSetupError
from locale import getpreferredencoding
import logging
from optparse import OptionParser
import os
import re
import shutil
import sys
import tempfile

from babel import __version__ as VERSION
from babel import Locale, localedata
from babel.core import UnknownLocaleError
from babel.messages.catalog import Catalog
from babel.messages.extract import extract_from_dir, DEFAULT_KEYWORDS, \
                                   DEFAULT_MAPPING
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po
from babel.util import odict, LOCALTZ
from babel._compat import string_types, BytesIO, PY2


class compile_catalog(Command):
    """Catalog compilation command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import compile_catalog

        setup(
            ...
            cmdclass = {'compile_catalog': compile_catalog}
        )

    .. versionadded:: 0.9
    """

    description = 'compile message catalogs to binary MO files'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('directory=', 'd',
         'path to base directory containing the catalogs'),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.mo')"),
        ('locale=', 'l',
         'locale of the catalog to compile'),
        ('use-fuzzy', 'f',
         'also include fuzzy translations'),
        ('statistics', None,
         'print statistics about translations')
    ]
    boolean_options = ['use-fuzzy', 'statistics']

    def initialize_options(self):
        self.domain = 'messages'
        self.directory = None
        self.input_file = None
        self.output_file = None
        self.locale = None
        self.use_fuzzy = False
        self.statistics = False

    def finalize_options(self):
        if not self.input_file and not self.directory:
            raise DistutilsOptionError('you must specify either the input file '
                                       'or the base directory')
        if not self.output_file and not self.directory:
            raise DistutilsOptionError('you must specify either the output file '
                                       'or the base directory')

    def run(self):
        po_files = []
        mo_files = []

        if not self.input_file:
            if self.locale:
                po_files.append((self.locale,
                                 os.path.join(self.directory, self.locale,
                                              'LC_MESSAGES',
                                              self.domain + '.po')))
                mo_files.append(os.path.join(self.directory, self.locale,
                                             'LC_MESSAGES',
                                             self.domain + '.mo'))
            else:
                for locale in os.listdir(self.directory):
                    po_file = os.path.join(self.directory, locale,
                                           'LC_MESSAGES', self.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
                        mo_files.append(os.path.join(self.directory, locale,
                                                     'LC_MESSAGES',
                                                     self.domain + '.mo'))
        else:
            po_files.append((self.locale, self.input_file))
            if self.output_file:
                mo_files.append(self.output_file)
            else:
                mo_files.append(os.path.join(self.directory, self.locale,
                                             'LC_MESSAGES',
                                             self.domain + '.mo'))

        if not po_files:
            raise DistutilsOptionError('no message catalogs found')

        for idx, (locale, po_file) in enumerate(po_files):
            mo_file = mo_files[idx]
            infile = open(po_file, 'rb')
            try:
                catalog = read_po(infile, locale)
            finally:
                infile.close()

            if self.statistics:
                translated = 0
                for message in list(catalog)[1:]:
                    if message.string:
                        translated +=1
                percentage = 0
                if len(catalog):
                    percentage = translated * 100 // len(catalog)
                log.info('%d of %d messages (%d%%) translated in %r',
                         translated, len(catalog), percentage, po_file)

            if catalog.fuzzy and not self.use_fuzzy:
                log.warn('catalog %r is marked as fuzzy, skipping', po_file)
                continue

            for message, errors in catalog.check():
                for error in errors:
                    log.error('error: %s:%d: %s', po_file, message.lineno,
                              error)

            log.info('compiling catalog %r to %r', po_file, mo_file)

            outfile = open(mo_file, 'wb')
            try:
                write_mo(outfile, catalog, use_fuzzy=self.use_fuzzy)
            finally:
                outfile.close()


class extract_messages(Command):
    """Message extraction command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import extract_messages

        setup(
            ...
            cmdclass = {'extract_messages': extract_messages}
        )
    """

    description = 'extract localizable strings from the project code'
    user_options = [
        ('charset=', None,
         'charset to use in the output file'),
        ('keywords=', 'k',
         'space-separated list of keywords to look for in addition to the '
         'defaults'),
        ('no-default-keywords', None,
         'do not include the default keywords'),
        ('mapping-file=', 'F',
         'path to the mapping configuration file'),
        ('no-location', None,
         'do not include location comments with filename and line number'),
        ('omit-header', None,
         'do not include msgid "" entry in header'),
        ('output-file=', 'o',
         'name of the output file'),
        ('width=', 'w',
         'set output line width (default 76)'),
        ('no-wrap', None,
         'do not break long message lines, longer than the output line width, '
         'into several lines'),
        ('sort-output', None,
         'generate sorted output (default False)'),
        ('sort-by-file', None,
         'sort output by file location (default False)'),
        ('msgid-bugs-address=', None,
         'set report address for msgid'),
        ('copyright-holder=', None,
         'set copyright holder in output'),
        ('add-comments=', 'c',
         'place comment block with TAG (or those preceding keyword lines) in '
         'output file. Separate multiple TAGs with commas(,)'),
        ('strip-comments', None,
         'strip the comment TAGs from the comments.'),
        ('input-dirs=', None,
         'directories that should be scanned for messages. Separate multiple '
         'directories with commas(,)'),
    ]
    boolean_options = [
        'no-default-keywords', 'no-location', 'omit-header', 'no-wrap',
        'sort-output', 'sort-by-file', 'strip-comments'
    ]

    def initialize_options(self):
        self.charset = 'utf-8'
        self.keywords = ''
        self._keywords = DEFAULT_KEYWORDS.copy()
        self.no_default_keywords = False
        self.mapping_file = None
        self.no_location = False
        self.omit_header = False
        self.output_file = None
        self.input_dirs = None
        self.width = None
        self.no_wrap = False
        self.sort_output = False
        self.sort_by_file = False
        self.msgid_bugs_address = None
        self.copyright_holder = None
        self.add_comments = None
        self._add_comments = []
        self.strip_comments = False

    def finalize_options(self):
        if self.no_default_keywords and not self.keywords:
            raise DistutilsOptionError('you must specify new keywords if you '
                                       'disable the default ones')
        if self.no_default_keywords:
            self._keywords = {}
        if self.keywords:
            self._keywords.update(parse_keywords(self.keywords.split()))

        if not self.output_file:
            raise DistutilsOptionError('no output file specified')
        if self.no_wrap and self.width:
            raise DistutilsOptionError("'--no-wrap' and '--width' are mutually "
                                       "exclusive")
        if not self.no_wrap and not self.width:
            self.width = 76
        elif self.width is not None:
            self.width = int(self.width)

        if self.sort_output and self.sort_by_file:
            raise DistutilsOptionError("'--sort-output' and '--sort-by-file' "
                                       "are mutually exclusive")

        if self.input_dirs:
            self.input_dirs = re.split(',\s*', self.input_dirs)
        else:
            self.input_dirs = dict.fromkeys([k.split('.',1)[0]
                for k in self.distribution.packages
            ]).keys()

        if self.add_comments:
            self._add_comments = self.add_comments.split(',')

    def run(self):
        mappings = self._get_mappings()
        outfile = open(self.output_file, 'wb')
        try:
            catalog = Catalog(project=self.distribution.get_name(),
                              version=self.distribution.get_version(),
                              msgid_bugs_address=self.msgid_bugs_address,
                              copyright_holder=self.copyright_holder,
                              charset=self.charset)

            for dirname, (method_map, options_map) in mappings.items():
                def callback(filename, method, options):
                    if method == 'ignore':
                        return
                    filepath = os.path.normpath(os.path.join(dirname, filename))
                    optstr = ''
                    if options:
                        optstr = ' (%s)' % ', '.join(['%s="%s"' % (k, v) for
                                                      k, v in options.items()])
                    log.info('extracting messages from %s%s', filepath, optstr)

                extracted = extract_from_dir(dirname, method_map, options_map,
                                             keywords=self._keywords,
                                             comment_tags=self._add_comments,
                                             callback=callback,
                                             strip_comment_tags=
                                                self.strip_comments)
                for filename, lineno, message, comments, context in extracted:
                    filepath = os.path.normpath(os.path.join(dirname, filename))
                    catalog.add(message, None, [(filepath, lineno)],
                                auto_comments=comments, context=context)

            log.info('writing PO template file to %s' % self.output_file)
            write_po(outfile, catalog, width=self.width,
                     no_location=self.no_location,
                     omit_header=self.omit_header,
                     sort_output=self.sort_output,
                     sort_by_file=self.sort_by_file)
        finally:
            outfile.close()

    def _get_mappings(self):
        mappings = {}

        if self.mapping_file:
            fileobj = open(self.mapping_file, 'U')
            try:
                method_map, options_map = parse_mapping(fileobj)
                for dirname in self.input_dirs:
                    mappings[dirname] = method_map, options_map
            finally:
                fileobj.close()

        elif getattr(self.distribution, 'message_extractors', None):
            message_extractors = self.distribution.message_extractors
            for dirname, mapping in message_extractors.items():
                if isinstance(mapping, string_types):
                    method_map, options_map = parse_mapping(BytesIO(mapping))
                else:
                    method_map, options_map = [], {}
                    for pattern, method, options in mapping:
                        method_map.append((pattern, method))
                        options_map[pattern] = options or {}
                mappings[dirname] = method_map, options_map

        else:
            for dirname in self.input_dirs:
                mappings[dirname] = DEFAULT_MAPPING, {}

        return mappings


def check_message_extractors(dist, name, value):
    """Validate the ``message_extractors`` keyword argument to ``setup()``.

    :param dist: the distutils/setuptools ``Distribution`` object
    :param name: the name of the keyword argument (should always be
                 "message_extractors")
    :param value: the value of the keyword argument
    :raise `DistutilsSetupError`: if the value is not valid
    """
    assert name == 'message_extractors'
    if not isinstance(value, dict):
        raise DistutilsSetupError('the value of the "message_extractors" '
                                  'parameter must be a dictionary')


class init_catalog(Command):
    """New catalog initialization command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import init_catalog

        setup(
            ...
            cmdclass = {'init_catalog': init_catalog}
        )
    """

    description = 'create a new catalog based on a POT file'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-dir=', 'd',
         'path to output directory'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.po')"),
        ('locale=', 'l',
         'locale for the new localized catalog'),
        ('width=', 'w',
         'set output line width (default 76)'),
        ('no-wrap', None,
         'do not break long message lines, longer than the output line width, '
         'into several lines'),
    ]
    boolean_options = ['no-wrap']

    def initialize_options(self):
        self.output_dir = None
        self.output_file = None
        self.input_file = None
        self.locale = None
        self.domain = 'messages'
        self.no_wrap = False
        self.width = None

    def finalize_options(self):
        if not self.input_file:
            raise DistutilsOptionError('you must specify the input file')

        if not self.locale:
            raise DistutilsOptionError('you must provide a locale for the '
                                       'new catalog')
        try:
            self._locale = Locale.parse(self.locale)
        except UnknownLocaleError as e:
            raise DistutilsOptionError(e)

        if not self.output_file and not self.output_dir:
            raise DistutilsOptionError('you must specify the output directory')
        if not self.output_file:
            self.output_file = os.path.join(self.output_dir, self.locale,
                                            'LC_MESSAGES', self.domain + '.po')

        if not os.path.exists(os.path.dirname(self.output_file)):
            os.makedirs(os.path.dirname(self.output_file))
        if self.no_wrap and self.width:
            raise DistutilsOptionError("'--no-wrap' and '--width' are mutually "
                                       "exclusive")
        if not self.no_wrap and not self.width:
            self.width = 76
        elif self.width is not None:
            self.width = int(self.width)

    def run(self):
        log.info('creating catalog %r based on %r', self.output_file,
                 self.input_file)

        infile = open(self.input_file, 'rb')
        try:
            # Although reading from the catalog template, read_po must be fed
            # the locale in order to correctly calculate plurals
            catalog = read_po(infile, locale=self.locale)
        finally:
            infile.close()

        catalog.locale = self._locale
        catalog.revision_date = datetime.now(LOCALTZ)
        catalog.fuzzy = False

        outfile = open(self.output_file, 'wb')
        try:
            write_po(outfile, catalog, width=self.width)
        finally:
            outfile.close()


class update_catalog(Command):
    """Catalog merging command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import update_catalog

        setup(
            ...
            cmdclass = {'update_catalog': update_catalog}
        )

    .. versionadded:: 0.9
    """

    description = 'update message catalogs from a POT file'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-dir=', 'd',
         'path to base directory containing the catalogs'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.po')"),
        ('locale=', 'l',
         'locale of the catalog to compile'),
        ('width=', 'w',
         'set output line width (default 76)'),
        ('no-wrap', None,
         'do not break long message lines, longer than the output line width, '
         'into several lines'),
        ('ignore-obsolete=', None,
         'whether to omit obsolete messages from the output'),
        ('no-fuzzy-matching', 'N',
         'do not use fuzzy matching'),
        ('previous', None,
         'keep previous msgids of translated messages')
    ]
    boolean_options = ['ignore_obsolete', 'no_fuzzy_matching', 'previous']

    def initialize_options(self):
        self.domain = 'messages'
        self.input_file = None
        self.output_dir = None
        self.output_file = None
        self.locale = None
        self.width = None
        self.no_wrap = False
        self.ignore_obsolete = False
        self.no_fuzzy_matching = False
        self.previous = False

    def finalize_options(self):
        if not self.input_file:
            raise DistutilsOptionError('you must specify the input file')
        if not self.output_file and not self.output_dir:
            raise DistutilsOptionError('you must specify the output file or '
                                       'directory')
        if self.output_file and not self.locale:
            raise DistutilsOptionError('you must specify the locale')
        if self.no_wrap and self.width:
            raise DistutilsOptionError("'--no-wrap' and '--width' are mutually "
                                       "exclusive")
        if not self.no_wrap and not self.width:
            self.width = 76
        elif self.width is not None:
            self.width = int(self.width)
        if self.no_fuzzy_matching and self.previous:
            self.previous = False

    def run(self):
        po_files = []
        if not self.output_file:
            if self.locale:
                po_files.append((self.locale,
                                 os.path.join(self.output_dir, self.locale,
                                              'LC_MESSAGES',
                                              self.domain + '.po')))
            else:
                for locale in os.listdir(self.output_dir):
                    po_file = os.path.join(self.output_dir, locale,
                                           'LC_MESSAGES',
                                           self.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
        else:
            po_files.append((self.locale, self.output_file))

        domain = self.domain
        if not domain:
            domain = os.path.splitext(os.path.basename(self.input_file))[0]

        infile = open(self.input_file, 'rb')
        try:
            template = read_po(infile)
        finally:
            infile.close()

        if not po_files:
            raise DistutilsOptionError('no message catalogs found')

        for locale, filename in po_files:
            log.info('updating catalog %r based on %r', filename,
                     self.input_file)
            infile = open(filename, 'rb')
            try:
                catalog = read_po(infile, locale=locale, domain=domain)
            finally:
                infile.close()

            catalog.update(template, self.no_fuzzy_matching)

            tmpname = os.path.join(os.path.dirname(filename),
                                   tempfile.gettempprefix() +
                                   os.path.basename(filename))
            tmpfile = open(tmpname, 'wb')
            try:
                try:
                    write_po(tmpfile, catalog,
                             ignore_obsolete=self.ignore_obsolete,
                             include_previous=self.previous, width=self.width)
                finally:
                    tmpfile.close()
            except:
                os.remove(tmpname)
                raise

            try:
                os.rename(tmpname, filename)
            except OSError:
                # We're probably on Windows, which doesn't support atomic
                # renames, at least not through Python
                # If the error is in fact due to a permissions problem, that
                # same error is going to be raised from one of the following
                # operations
                os.remove(filename)
                shutil.copy(tmpname, filename)
                os.remove(tmpname)


class CommandLineInterface(object):
    """Command-line interface.

    This class provides a simple command-line interface to the message
    extraction and PO file generation functionality.
    """

    usage = '%%prog %s [options] %s'
    version = '%%prog %s' % VERSION
    commands = {
        'compile': 'compile message catalogs to MO files',
        'extract': 'extract messages from source files and generate a POT file',
        'init':    'create new message catalogs from a POT file',
        'update':  'update existing message catalogs from a POT file'
    }

    def run(self, argv=sys.argv):
        """Main entry point of the command-line interface.

        :param argv: list of arguments passed on the command-line
        """
        self.parser = OptionParser(usage=self.usage % ('command', '[args]'),
                                   version=self.version)
        self.parser.disable_interspersed_args()
        self.parser.print_help = self._help
        self.parser.add_option('--list-locales', dest='list_locales',
                               action='store_true',
                               help="print all known locales and exit")
        self.parser.add_option('-v', '--verbose', action='store_const',
                               dest='loglevel', const=logging.DEBUG,
                               help='print as much as possible')
        self.parser.add_option('-q', '--quiet', action='store_const',
                               dest='loglevel', const=logging.ERROR,
                               help='print as little as possible')
        self.parser.set_defaults(list_locales=False, loglevel=logging.INFO)

        options, args = self.parser.parse_args(argv[1:])

        self._configure_logging(options.loglevel)
        if options.list_locales:
            identifiers = localedata.locale_identifiers()
            longest = max([len(identifier) for identifier in identifiers])
            identifiers.sort()
            format = u'%%-%ds %%s' % (longest + 1)
            for identifier in identifiers:
                locale = Locale.parse(identifier)
                output = format % (identifier, locale.english_name)
                print(output.encode(sys.stdout.encoding or
                                    getpreferredencoding() or
                                    'ascii', 'replace'))
            return 0

        if not args:
            self.parser.error('no valid command or option passed. '
                              'Try the -h/--help option for more information.')

        cmdname = args[0]
        if cmdname not in self.commands:
            self.parser.error('unknown command "%s"' % cmdname)

        return getattr(self, cmdname)(args[1:])

    def _configure_logging(self, loglevel):
        self.log = logging.getLogger('babel')
        self.log.setLevel(loglevel)
        # Don't add a new handler for every instance initialization (#227), this
        # would cause duplicated output when the CommandLineInterface as an
        # normal Python class.
        if self.log.handlers:
            handler = self.log.handlers[0]
        else:
            handler = logging.StreamHandler()
            self.log.addHandler(handler)
        handler.setLevel(loglevel)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

    def _help(self):
        print(self.parser.format_help())
        print("commands:")
        longest = max([len(command) for command in self.commands])
        format = "  %%-%ds %%s" % max(8, longest + 1)
        commands = sorted(self.commands.items())
        for name, description in commands:
            print(format % (name, description))

    def compile(self, argv):
        """Subcommand for compiling a message catalog to a MO file.

        :param argv: the command arguments
        :since: version 0.9
        """
        parser = OptionParser(usage=self.usage % ('compile', ''),
                              description=self.commands['compile'])
        parser.add_option('--domain', '-D', dest='domain',
                          help="domain of MO and PO files (default '%default')")
        parser.add_option('--directory', '-d', dest='directory',
                          metavar='DIR', help='base directory of catalog files')
        parser.add_option('--locale', '-l', dest='locale', metavar='LOCALE',
                          help='locale of the catalog')
        parser.add_option('--input-file', '-i', dest='input_file',
                          metavar='FILE', help='name of the input file')
        parser.add_option('--output-file', '-o', dest='output_file',
                          metavar='FILE',
                          help="name of the output file (default "
                               "'<output_dir>/<locale>/LC_MESSAGES/"
                               "<domain>.mo')")
        parser.add_option('--use-fuzzy', '-f', dest='use_fuzzy',
                          action='store_true',
                          help='also include fuzzy translations (default '
                               '%default)')
        parser.add_option('--statistics', dest='statistics',
                          action='store_true',
                          help='print statistics about translations')

        parser.set_defaults(domain='messages', use_fuzzy=False,
                            compile_all=False, statistics=False)
        options, args = parser.parse_args(argv)

        po_files = []
        mo_files = []
        if not options.input_file:
            if not options.directory:
                parser.error('you must specify either the input file or the '
                             'base directory')
            if options.locale:
                po_files.append((options.locale,
                                 os.path.join(options.directory,
                                              options.locale, 'LC_MESSAGES',
                                              options.domain + '.po')))
                mo_files.append(os.path.join(options.directory, options.locale,
                                             'LC_MESSAGES',
                                             options.domain + '.mo'))
            else:
                for locale in os.listdir(options.directory):
                    po_file = os.path.join(options.directory, locale,
                                           'LC_MESSAGES', options.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
                        mo_files.append(os.path.join(options.directory, locale,
                                                     'LC_MESSAGES',
                                                     options.domain + '.mo'))
        else:
            po_files.append((options.locale, options.input_file))
            if options.output_file:
                mo_files.append(options.output_file)
            else:
                if not options.directory:
                    parser.error('you must specify either the output file or '
                                 'the base directory')
                mo_files.append(os.path.join(options.directory, options.locale,
                                             'LC_MESSAGES',
                                             options.domain + '.mo'))
        if not po_files:
            parser.error('no message catalogs found')

        for idx, (locale, po_file) in enumerate(po_files):
            mo_file = mo_files[idx]
            infile = open(po_file, 'rb')
            try:
                catalog = read_po(infile, locale)
            finally:
                infile.close()

            if options.statistics:
                translated = 0
                for message in list(catalog)[1:]:
                    if message.string:
                        translated +=1
                percentage = 0
                if len(catalog):
                    percentage = translated * 100 // len(catalog)
                self.log.info("%d of %d messages (%d%%) translated in %r",
                              translated, len(catalog), percentage, po_file)

            if catalog.fuzzy and not options.use_fuzzy:
                self.log.warning('catalog %r is marked as fuzzy, skipping',
                                 po_file)
                continue

            for message, errors in catalog.check():
                for error in errors:
                    self.log.error('error: %s:%d: %s', po_file, message.lineno,
                                   error)

            self.log.info('compiling catalog %r to %r', po_file, mo_file)

            outfile = open(mo_file, 'wb')
            try:
                write_mo(outfile, catalog, use_fuzzy=options.use_fuzzy)
            finally:
                outfile.close()

    def extract(self, argv):
        """Subcommand for extracting messages from source files and generating
        a POT file.

        :param argv: the command arguments
        """
        parser = OptionParser(usage=self.usage % ('extract', 'dir1 <dir2> ...'),
                              description=self.commands['extract'])
        parser.add_option('--charset', dest='charset',
                          help='charset to use in the output (default '
                               '"%default")')
        parser.add_option('-k', '--keyword', dest='keywords', action='append',
                          help='keywords to look for in addition to the '
                               'defaults. You can specify multiple -k flags on '
                               'the command line.')
        parser.add_option('--no-default-keywords', dest='no_default_keywords',
                          action='store_true',
                          help="do not include the default keywords")
        parser.add_option('--mapping', '-F', dest='mapping_file',
                          help='path to the extraction mapping file')
        parser.add_option('--no-location', dest='no_location',
                          action='store_true',
                          help='do not include location comments with filename '
                               'and line number')
        parser.add_option('--omit-header', dest='omit_header',
                          action='store_true',
                          help='do not include msgid "" entry in header')
        parser.add_option('-o', '--output', dest='output',
                          help='path to the output POT file')
        parser.add_option('-w', '--width', dest='width', type='int',
                          help="set output line width (default 76)")
        parser.add_option('--no-wrap', dest='no_wrap', action='store_true',
                          help='do not break long message lines, longer than '
                               'the output line width, into several lines')
        parser.add_option('--sort-output', dest='sort_output',
                          action='store_true',
                          help='generate sorted output (default False)')
        parser.add_option('--sort-by-file', dest='sort_by_file',
                          action='store_true',
                          help='sort output by file location (default False)')
        parser.add_option('--msgid-bugs-address', dest='msgid_bugs_address',
                          metavar='EMAIL@ADDRESS',
                          help='set report address for msgid')
        parser.add_option('--copyright-holder', dest='copyright_holder',
                          help='set copyright holder in output')
        parser.add_option('--project', dest='project',
                          help='set project name in output')
        parser.add_option('--version', dest='version',
                          help='set project version in output')
        parser.add_option('--add-comments', '-c', dest='comment_tags',
                          metavar='TAG', action='append',
                          help='place comment block with TAG (or those '
                               'preceding keyword lines) in output file. One '
                               'TAG per argument call')
        parser.add_option('--strip-comment-tags', '-s',
                          dest='strip_comment_tags', action='store_true',
                          help='Strip the comment tags from the comments.')

        parser.set_defaults(charset='utf-8', keywords=[],
                            no_default_keywords=False, no_location=False,
                            omit_header = False, width=None, no_wrap=False,
                            sort_output=False, sort_by_file=False,
                            comment_tags=[], strip_comment_tags=False)
        options, args = parser.parse_args(argv)
        if not args:
            parser.error('incorrect number of arguments')

        keywords = DEFAULT_KEYWORDS.copy()
        if options.no_default_keywords:
            if not options.keywords:
                parser.error('you must specify new keywords if you disable the '
                             'default ones')
            keywords = {}
        if options.keywords:
            keywords.update(parse_keywords(options.keywords))

        if options.mapping_file:
            fileobj = open(options.mapping_file, 'U')
            try:
                method_map, options_map = parse_mapping(fileobj)
            finally:
                fileobj.close()
        else:
            method_map = DEFAULT_MAPPING
            options_map = {}

        if options.width and options.no_wrap:
            parser.error("'--no-wrap' and '--width' are mutually exclusive.")
        elif not options.width and not options.no_wrap:
            options.width = 76

        if options.sort_output and options.sort_by_file:
            parser.error("'--sort-output' and '--sort-by-file' are mutually "
                         "exclusive")

        catalog = Catalog(project=options.project,
                          version=options.version,
                          msgid_bugs_address=options.msgid_bugs_address,
                          copyright_holder=options.copyright_holder,
                          charset=options.charset)

        for dirname in args:
            if not os.path.isdir(dirname):
                parser.error('%r is not a directory' % dirname)

            def callback(filename, method, options):
                if method == 'ignore':
                    return
                filepath = os.path.normpath(os.path.join(dirname, filename))
                optstr = ''
                if options:
                    optstr = ' (%s)' % ', '.join(['%s="%s"' % (k, v) for
                                                  k, v in options.items()])
                self.log.info('extracting messages from %s%s', filepath,
                              optstr)

            extracted = extract_from_dir(dirname, method_map, options_map,
                                         keywords, options.comment_tags,
                                         callback=callback,
                                         strip_comment_tags=
                                            options.strip_comment_tags)
            for filename, lineno, message, comments, context in extracted:
                filepath = os.path.normpath(os.path.join(dirname, filename))
                catalog.add(message, None, [(filepath, lineno)],
                            auto_comments=comments, context=context)

        catalog_charset = catalog.charset
        if options.output not in (None, '-'):
            self.log.info('writing PO template file to %s' % options.output)
            outfile = open(options.output, 'wb')
            close_output = True
        else:
            outfile = sys.stdout

            # This is a bit of a hack on Python 3.  stdout is a text stream so
            # we need to find the underlying file when we write the PO.  In
            # later versions of Babel we want the write_po function to accept
            # text or binary streams and automatically adjust the encoding.
            if not PY2 and hasattr(outfile, 'buffer'):
                catalog.charset = outfile.encoding
                outfile = outfile.buffer.raw

            close_output = False

        try:
            write_po(outfile, catalog, width=options.width,
                     no_location=options.no_location,
                     omit_header=options.omit_header,
                     sort_output=options.sort_output,
                     sort_by_file=options.sort_by_file)
        finally:
            if close_output:
                outfile.close()
            catalog.charset = catalog_charset

    def init(self, argv):
        """Subcommand for creating new message catalogs from a template.

        :param argv: the command arguments
        """
        parser = OptionParser(usage=self.usage % ('init', ''),
                              description=self.commands['init'])
        parser.add_option('--domain', '-D', dest='domain',
                          help="domain of PO file (default '%default')")
        parser.add_option('--input-file', '-i', dest='input_file',
                          metavar='FILE', help='name of the input file')
        parser.add_option('--output-dir', '-d', dest='output_dir',
                          metavar='DIR', help='path to output directory')
        parser.add_option('--output-file', '-o', dest='output_file',
                          metavar='FILE',
                          help="name of the output file (default "
                               "'<output_dir>/<locale>/LC_MESSAGES/"
                               "<domain>.po')")
        parser.add_option('--locale', '-l', dest='locale', metavar='LOCALE',
                          help='locale for the new localized catalog')
        parser.add_option('-w', '--width', dest='width', type='int',
                          help="set output line width (default 76)")
        parser.add_option('--no-wrap', dest='no_wrap', action='store_true',
                          help='do not break long message lines, longer than '
                               'the output line width, into several lines')

        parser.set_defaults(domain='messages')
        options, args = parser.parse_args(argv)

        if not options.locale:
            parser.error('you must provide a locale for the new catalog')
        try:
            locale = Locale.parse(options.locale)
        except UnknownLocaleError as e:
            parser.error(e)

        if not options.input_file:
            parser.error('you must specify the input file')

        if not options.output_file and not options.output_dir:
            parser.error('you must specify the output file or directory')

        if not options.output_file:
            options.output_file = os.path.join(options.output_dir,
                                               options.locale, 'LC_MESSAGES',
                                               options.domain + '.po')
        if not os.path.exists(os.path.dirname(options.output_file)):
            os.makedirs(os.path.dirname(options.output_file))
        if options.width and options.no_wrap:
            parser.error("'--no-wrap' and '--width' are mutually exclusive.")
        elif not options.width and not options.no_wrap:
            options.width = 76

        infile = open(options.input_file, 'r')
        try:
            # Although reading from the catalog template, read_po must be fed
            # the locale in order to correctly calculate plurals
            catalog = read_po(infile, locale=options.locale)
        finally:
            infile.close()

        catalog.locale = locale
        catalog.revision_date = datetime.now(LOCALTZ)

        self.log.info('creating catalog %r based on %r', options.output_file,
                      options.input_file)

        outfile = open(options.output_file, 'wb')
        try:
            write_po(outfile, catalog, width=options.width)
        finally:
            outfile.close()

    def update(self, argv):
        """Subcommand for updating existing message catalogs from a template.

        :param argv: the command arguments
        :since: version 0.9
        """
        parser = OptionParser(usage=self.usage % ('update', ''),
                              description=self.commands['update'])
        parser.add_option('--domain', '-D', dest='domain',
                          help="domain of PO file (default '%default')")
        parser.add_option('--input-file', '-i', dest='input_file',
                          metavar='FILE', help='name of the input file')
        parser.add_option('--output-dir', '-d', dest='output_dir',
                          metavar='DIR', help='path to output directory')
        parser.add_option('--output-file', '-o', dest='output_file',
                          metavar='FILE',
                          help="name of the output file (default "
                               "'<output_dir>/<locale>/LC_MESSAGES/"
                               "<domain>.po')")
        parser.add_option('--locale', '-l', dest='locale', metavar='LOCALE',
                          help='locale of the translations catalog')
        parser.add_option('-w', '--width', dest='width', type='int',
                          help="set output line width (default 76)")
        parser.add_option('--no-wrap', dest='no_wrap', action = 'store_true',
                          help='do not break long message lines, longer than '
                               'the output line width, into several lines')
        parser.add_option('--ignore-obsolete', dest='ignore_obsolete',
                          action='store_true',
                          help='do not include obsolete messages in the output '
                               '(default %default)')
        parser.add_option('--no-fuzzy-matching', '-N', dest='no_fuzzy_matching',
                          action='store_true',
                          help='do not use fuzzy matching (default %default)')
        parser.add_option('--previous', dest='previous', action='store_true',
                          help='keep previous msgids of translated messages '
                               '(default %default)')

        parser.set_defaults(domain='messages', ignore_obsolete=False,
                            no_fuzzy_matching=False, previous=False)
        options, args = parser.parse_args(argv)

        if not options.input_file:
            parser.error('you must specify the input file')
        if not options.output_file and not options.output_dir:
            parser.error('you must specify the output file or directory')
        if options.output_file and not options.locale:
            parser.error('you must specify the locale')
        if options.no_fuzzy_matching and options.previous:
            options.previous = False

        po_files = []
        if not options.output_file:
            if options.locale:
                po_files.append((options.locale,
                                 os.path.join(options.output_dir,
                                              options.locale, 'LC_MESSAGES',
                                              options.domain + '.po')))
            else:
                for locale in os.listdir(options.output_dir):
                    po_file = os.path.join(options.output_dir, locale,
                                           'LC_MESSAGES',
                                           options.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
        else:
            po_files.append((options.locale, options.output_file))

        domain = options.domain
        if not domain:
            domain = os.path.splitext(os.path.basename(options.input_file))[0]

        infile = open(options.input_file, 'U')
        try:
            template = read_po(infile)
        finally:
            infile.close()

        if not po_files:
            parser.error('no message catalogs found')

        if options.width and options.no_wrap:
            parser.error("'--no-wrap' and '--width' are mutually exclusive.")
        elif not options.width and not options.no_wrap:
            options.width = 76
        for locale, filename in po_files:
            self.log.info('updating catalog %r based on %r', filename,
                          options.input_file)
            infile = open(filename, 'U')
            try:
                catalog = read_po(infile, locale=locale, domain=domain)
            finally:
                infile.close()

            catalog.update(template, options.no_fuzzy_matching)

            tmpname = os.path.join(os.path.dirname(filename),
                                   tempfile.gettempprefix() +
                                   os.path.basename(filename))
            tmpfile = open(tmpname, 'wb')
            try:
                try:
                    write_po(tmpfile, catalog,
                             ignore_obsolete=options.ignore_obsolete,
                             include_previous=options.previous,
                             width=options.width)
                finally:
                    tmpfile.close()
            except:
                os.remove(tmpname)
                raise

            try:
                os.rename(tmpname, filename)
            except OSError:
                # We're probably on Windows, which doesn't support atomic
                # renames, at least not through Python
                # If the error is in fact due to a permissions problem, that
                # same error is going to be raised from one of the following
                # operations
                os.remove(filename)
                shutil.copy(tmpname, filename)
                os.remove(tmpname)


def main():
    return CommandLineInterface().run(sys.argv)


def parse_mapping(fileobj, filename=None):
    """Parse an extraction method mapping from a file-like object.

    >>> buf = BytesIO(b'''
    ... [extractors]
    ... custom = mypackage.module:myfunc
    ...
    ... # Python source files
    ... [python: **.py]
    ...
    ... # Genshi templates
    ... [genshi: **/templates/**.html]
    ... include_attrs =
    ... [genshi: **/templates/**.txt]
    ... template_class = genshi.template:TextTemplate
    ... encoding = latin-1
    ...
    ... # Some custom extractor
    ... [custom: **/custom/*.*]
    ... ''')

    >>> method_map, options_map = parse_mapping(buf)
    >>> len(method_map)
    4

    >>> method_map[0]
    ('**.py', 'python')
    >>> options_map['**.py']
    {}
    >>> method_map[1]
    ('**/templates/**.html', 'genshi')
    >>> options_map['**/templates/**.html']['include_attrs']
    ''
    >>> method_map[2]
    ('**/templates/**.txt', 'genshi')
    >>> options_map['**/templates/**.txt']['template_class']
    'genshi.template:TextTemplate'
    >>> options_map['**/templates/**.txt']['encoding']
    'latin-1'

    >>> method_map[3]
    ('**/custom/*.*', 'mypackage.module:myfunc')
    >>> options_map['**/custom/*.*']
    {}

    :param fileobj: a readable file-like object containing the configuration
                    text to parse
    :see: `extract_from_directory`
    """
    extractors = {}
    method_map = []
    options_map = {}

    parser = RawConfigParser()
    parser._sections = odict(parser._sections) # We need ordered sections
    parser.readfp(fileobj, filename)
    for section in parser.sections():
        if section == 'extractors':
            extractors = dict(parser.items(section))
        else:
            method, pattern = [part.strip() for part in section.split(':', 1)]
            method_map.append((pattern, method))
            options_map[pattern] = dict(parser.items(section))

    if extractors:
        for idx, (pattern, method) in enumerate(method_map):
            if method in extractors:
                method = extractors[method]
            method_map[idx] = (pattern, method)

    return (method_map, options_map)


def parse_keywords(strings=[]):
    """Parse keywords specifications from the given list of strings.

    >>> kw = parse_keywords(['_', 'dgettext:2', 'dngettext:2,3', 'pgettext:1c,2']).items()
    >>> kw.sort()
    >>> for keyword, indices in kw:
    ...     print (keyword, indices)
    ('_', None)
    ('dgettext', (2,))
    ('dngettext', (2, 3))
    ('pgettext', ((1, 'c'), 2))
    """
    keywords = {}
    for string in strings:
        if ':' in string:
            funcname, indices = string.split(':')
        else:
            funcname, indices = string, None
        if funcname not in keywords:
            if indices:
                inds = []
                for x in indices.split(','):
                    if x[-1] == 'c':
                        inds.append((int(x[:-1]), 'c'))
                    else:
                        inds.append(int(x))
                indices = tuple(inds)
            keywords[funcname] = indices
    return keywords


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = jslexer
# -*- coding: utf-8 -*-
"""
    babel.messages.jslexer
    ~~~~~~~~~~~~~~~~~~~~~~

    A simple JavaScript 1.5 lexer which is used for the JavaScript
    extractor.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

from operator import itemgetter
import re
from babel._compat import unichr

operators = [
    '+', '-', '*', '%', '!=', '==', '<', '>', '<=', '>=', '=',
    '+=', '-=', '*=', '%=', '<<', '>>', '>>>', '<<=', '>>=',
    '>>>=', '&', '&=', '|', '|=', '&&', '||', '^', '^=', '(', ')',
    '[', ']', '{', '}', '!', '--', '++', '~', ',', ';', '.', ':'
]
operators.sort(key=lambda a: -len(a))

escapes = {'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'}

rules = [
    (None, re.compile(r'\s+(?u)')),
    (None, re.compile(r'<!--.*')),
    ('linecomment', re.compile(r'//.*')),
    ('multilinecomment', re.compile(r'/\*.*?\*/(?us)')),
    ('name', re.compile(r'(\$+\w*|[^\W\d]\w*)(?u)')),
    ('number', re.compile(r'''(?x)(
        (?:0|[1-9]\d*)
        (\.\d+)?
        ([eE][-+]?\d+)? |
        (0x[a-fA-F0-9]+)
    )''')),
    ('operator', re.compile(r'(%s)' % '|'.join(map(re.escape, operators)))),
    ('string', re.compile(r'''(?xs)(
        '(?:[^'\\]*(?:\\.[^'\\]*)*)'  |
        "(?:[^"\\]*(?:\\.[^"\\]*)*)"
    )'''))
]

division_re = re.compile(r'/=?')
regex_re = re.compile(r'/(?:[^/\\]*(?:\\.[^/\\]*)*)/[a-zA-Z]*(?s)')
line_re = re.compile(r'(\r\n|\n|\r)')
line_join_re = re.compile(r'\\' + line_re.pattern)
uni_escape_re = re.compile(r'[a-fA-F0-9]{1,4}')


class Token(tuple):
    """Represents a token as returned by `tokenize`."""
    __slots__ = ()

    def __new__(cls, type, value, lineno):
        return tuple.__new__(cls, (type, value, lineno))

    type = property(itemgetter(0))
    value = property(itemgetter(1))
    lineno = property(itemgetter(2))


def indicates_division(token):
    """A helper function that helps the tokenizer to decide if the current
    token may be followed by a division operator.
    """
    if token.type == 'operator':
        return token.value in (')', ']', '}', '++', '--')
    return token.type in ('name', 'number', 'string', 'regexp')


def unquote_string(string):
    """Unquote a string with JavaScript rules.  The string has to start with
    string delimiters (``'`` or ``"``.)
    """
    assert string and string[0] == string[-1] and string[0] in '"\'', \
        'string provided is not properly delimited'
    string = line_join_re.sub('\\1', string[1:-1])
    result = []
    add = result.append
    pos = 0

    while 1:
        # scan for the next escape
        escape_pos = string.find('\\', pos)
        if escape_pos < 0:
            break
        add(string[pos:escape_pos])

        # check which character is escaped
        next_char = string[escape_pos + 1]
        if next_char in escapes:
            add(escapes[next_char])

        # unicode escapes.  trie to consume up to four characters of
        # hexadecimal characters and try to interpret them as unicode
        # character point.  If there is no such character point, put
        # all the consumed characters into the string.
        elif next_char in 'uU':
            escaped = uni_escape_re.match(string, escape_pos + 2)
            if escaped is not None:
                escaped_value = escaped.group()
                if len(escaped_value) == 4:
                    try:
                        add(unichr(int(escaped_value, 16)))
                    except ValueError:
                        pass
                    else:
                        pos = escape_pos + 6
                        continue
                add(next_char + escaped_value)
                pos = escaped.end()
                continue
            else:
                add(next_char)

        # bogus escape.  Just remove the backslash.
        else:
            add(next_char)
        pos = escape_pos + 2

    if pos < len(string):
        add(string[pos:])

    return u''.join(result)


def tokenize(source):
    """Tokenize a JavaScript source.  Returns a generator of tokens.
    """
    may_divide = False
    pos = 0
    lineno = 1
    end = len(source)

    while pos < end:
        # handle regular rules first
        for token_type, rule in rules:
            match = rule.match(source, pos)
            if match is not None:
                break
        # if we don't have a match we don't give up yet, but check for
        # division operators or regular expression literals, based on
        # the status of `may_divide` which is determined by the last
        # processed non-whitespace token using `indicates_division`.
        else:
            if may_divide:
                match = division_re.match(source, pos)
                token_type = 'operator'
            else:
                match = regex_re.match(source, pos)
                token_type = 'regexp'
            if match is None:
                # woops. invalid syntax. jump one char ahead and try again.
                pos += 1
                continue

        token_value = match.group()
        if token_type is not None:
            token = Token(token_type, token_value, lineno)
            may_divide = indicates_division(token)
            yield token
        lineno += len(line_re.findall(token_value))
        pos = match.end()

########NEW FILE########
__FILENAME__ = mofile
# -*- coding: utf-8 -*-
"""
    babel.messages.mofile
    ~~~~~~~~~~~~~~~~~~~~~

    Writing of files in the ``gettext`` MO (machine object) format.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import array
import struct

from babel.messages.catalog import Catalog, Message
from babel._compat import range_type, array_tobytes


LE_MAGIC = 0x950412de
BE_MAGIC = 0xde120495


def read_mo(fileobj):
    """Read a binary MO file from the given file-like object and return a
    corresponding `Catalog` object.

    :param fileobj: the file-like object to read the MO file from

    :note: The implementation of this function is heavily based on the
           ``GNUTranslations._parse`` method of the ``gettext`` module in the
           standard library.
    """
    catalog = Catalog()
    headers = {}

    filename = getattr(fileobj, 'name', '')

    buf = fileobj.read()
    buflen = len(buf)
    unpack = struct.unpack

    # Parse the .mo file header, which consists of 5 little endian 32
    # bit words.
    magic = unpack('<I', buf[:4])[0] # Are we big endian or little endian?
    if magic == LE_MAGIC:
        version, msgcount, origidx, transidx = unpack('<4I', buf[4:20])
        ii = '<II'
    elif magic == BE_MAGIC:
        version, msgcount, origidx, transidx = unpack('>4I', buf[4:20])
        ii = '>II'
    else:
        raise IOError(0, 'Bad magic number', filename)

    # Now put all messages from the .mo file buffer into the catalog
    # dictionary
    for i in range_type(0, msgcount):
        mlen, moff = unpack(ii, buf[origidx:origidx + 8])
        mend = moff + mlen
        tlen, toff = unpack(ii, buf[transidx:transidx + 8])
        tend = toff + tlen
        if mend < buflen and tend < buflen:
            msg = buf[moff:mend]
            tmsg = buf[toff:tend]
        else:
            raise IOError(0, 'File is corrupt', filename)

        # See if we're looking at GNU .mo conventions for metadata
        if mlen == 0:
            # Catalog description
            lastkey = key = None
            for item in tmsg.splitlines():
                item = item.strip()
                if not item:
                    continue
                if b':' in item:
                    key, value = item.split(b':', 1)
                    lastkey = key = key.strip().lower()
                    headers[key] = value.strip()
                elif lastkey:
                    headers[lastkey] += b'\n' + item

        if b'\x04' in msg: # context
            ctxt, msg = msg.split(b'\x04')
        else:
            ctxt = None

        if b'\x00' in msg: # plural forms
            msg = msg.split(b'\x00')
            tmsg = tmsg.split(b'\x00')
            if catalog.charset:
                msg = [x.decode(catalog.charset) for x in msg]
                tmsg = [x.decode(catalog.charset) for x in tmsg]
        else:
            if catalog.charset:
                msg = msg.decode(catalog.charset)
                tmsg = tmsg.decode(catalog.charset)
        catalog[msg] = Message(msg, tmsg, context=ctxt)

        # advance to next entry in the seek tables
        origidx += 8
        transidx += 8

    catalog.mime_headers = headers.items()
    return catalog


def write_mo(fileobj, catalog, use_fuzzy=False):
    """Write a catalog to the specified file-like object using the GNU MO file
    format.

    >>> from babel.messages import Catalog
    >>> from gettext import GNUTranslations
    >>> from StringIO import StringIO

    >>> catalog = Catalog(locale='en_US')
    >>> catalog.add('foo', 'Voh')
    <Message ...>
    >>> catalog.add((u'bar', u'baz'), (u'Bahr', u'Batz'))
    <Message ...>
    >>> catalog.add('fuz', 'Futz', flags=['fuzzy'])
    <Message ...>
    >>> catalog.add('Fizz', '')
    <Message ...>
    >>> catalog.add(('Fuzz', 'Fuzzes'), ('', ''))
    <Message ...>
    >>> buf = StringIO()

    >>> write_mo(buf, catalog)
    >>> buf.seek(0)
    >>> translations = GNUTranslations(fp=buf)
    >>> translations.ugettext('foo')
    u'Voh'
    >>> translations.ungettext('bar', 'baz', 1)
    u'Bahr'
    >>> translations.ungettext('bar', 'baz', 2)
    u'Batz'
    >>> translations.ugettext('fuz')
    u'fuz'
    >>> translations.ugettext('Fizz')
    u'Fizz'
    >>> translations.ugettext('Fuzz')
    u'Fuzz'
    >>> translations.ugettext('Fuzzes')
    u'Fuzzes'

    :param fileobj: the file-like object to write to
    :param catalog: the `Catalog` instance
    :param use_fuzzy: whether translations marked as "fuzzy" should be included
                      in the output
    """
    messages = list(catalog)
    if not use_fuzzy:
        messages[1:] = [m for m in messages[1:] if not m.fuzzy]
    messages.sort()

    ids = strs = b''
    offsets = []

    for message in messages:
        # For each string, we need size and file offset.  Each string is NUL
        # terminated; the NUL does not count into the size.
        if message.pluralizable:
            msgid = b'\x00'.join([
                msgid.encode(catalog.charset) for msgid in message.id
            ])
            msgstrs = []
            for idx, string in enumerate(message.string):
                if not string:
                    msgstrs.append(message.id[min(int(idx), 1)])
                else:
                    msgstrs.append(string)
            msgstr = b'\x00'.join([
                msgstr.encode(catalog.charset) for msgstr in msgstrs
            ])
        else:
            msgid = message.id.encode(catalog.charset)
            if not message.string:
                msgstr = message.id.encode(catalog.charset)
            else:
                msgstr = message.string.encode(catalog.charset)
        if message.context:
            msgid = b'\x04'.join([message.context.encode(catalog.charset),
                                 msgid])
        offsets.append((len(ids), len(msgid), len(strs), len(msgstr)))
        ids += msgid + b'\x00'
        strs += msgstr + b'\x00'

    # The header is 7 32-bit unsigned integers.  We don't use hash tables, so
    # the keys start right after the index tables.
    keystart = 7 * 4 + 16 * len(messages)
    valuestart = keystart + len(ids)

    # The string table first has the list of keys, then the list of values.
    # Each entry has first the size of the string, then the file offset.
    koffsets = []
    voffsets = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    offsets = koffsets + voffsets

    fileobj.write(struct.pack('Iiiiiii',
        LE_MAGIC,                   # magic
        0,                          # version
        len(messages),              # number of entries
        7 * 4,                      # start of key index
        7 * 4 + len(messages) * 8,  # start of value index
        0, 0                        # size and offset of hash table
    ) + array_tobytes(array.array("i", offsets)) + ids + strs)

########NEW FILE########
__FILENAME__ = plurals
# -*- coding: utf-8 -*-
"""
    babel.messages.plurals
    ~~~~~~~~~~~~~~~~~~~~~~

    Plural form definitions.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

from babel.core import default_locale, Locale
from operator import itemgetter


# XXX: remove this file, duplication with babel.plural


LC_CTYPE = default_locale('LC_CTYPE')


PLURALS = {
    # Afar
    # 'aa': (),
    # Abkhazian
    # 'ab': (),
    # Avestan
    # 'ae': (),
    # Afrikaans - From Pootle's PO's
    'af': (2, '(n != 1)'),
    # Akan
    # 'ak': (),
    # Amharic
    # 'am': (),
    # Aragonese
    # 'an': (),
    # Arabic - From Pootle's PO's
    'ar': (6, '(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n>=3 && n<=10 ? 3 : n>=11 && n<=99 ? 4 : 5)'),
    # Assamese
    # 'as': (),
    # Avaric
    # 'av': (),
    # Aymara
    # 'ay': (),
    # Azerbaijani
    # 'az': (),
    # Bashkir
    # 'ba': (),
    # Belarusian
    # 'be': (),
    # Bulgarian - From Pootle's PO's
    'bg': (2, '(n != 1)'),
    # Bihari
    # 'bh': (),
    # Bislama
    # 'bi': (),
    # Bambara
    # 'bm': (),
    # Bengali - From Pootle's PO's
    'bn': (2, '(n != 1)'),
    # Tibetan - as discussed in private with Andrew West
    'bo': (1, '0'),
    # Breton
    # 'br': (),
    # Bosnian
    # 'bs': (),
    # Catalan - From Pootle's PO's
    'ca': (2, '(n != 1)'),
    # Chechen
    # 'ce': (),
    # Chamorro
    # 'ch': (),
    # Corsican
    # 'co': (),
    # Cree
    # 'cr': (),
    # Czech
    'cs': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Church Slavic
    # 'cu': (),
    # Chuvash
    'cv': (1, '0'),
    # Welsh
    'cy': (5, '(n==1 ? 1 : n==2 ? 2 : n==3 ? 3 : n==6 ? 4 : 0)'),
    # Danish
    'da': (2, '(n != 1)'),
    # German
    'de': (2, '(n != 1)'),
    # Divehi
    # 'dv': (),
    # Dzongkha
    'dz': (1, '0'),
    # Greek
    'el': (2, '(n != 1)'),
    # English
    'en': (2, '(n != 1)'),
    # Esperanto
    'eo': (2, '(n != 1)'),
    # Spanish
    'es': (2, '(n != 1)'),
    # Estonian
    'et': (2, '(n != 1)'),
    # Basque - From Pootle's PO's
    'eu': (2, '(n != 1)'),
    # Persian - From Pootle's PO's
    'fa': (1, '0'),
    # Finnish
    'fi': (2, '(n != 1)'),
    # French
    'fr': (2, '(n > 1)'),
    # Friulian - From Pootle's PO's
    'fur': (2, '(n > 1)'),
    # Irish
    'ga': (3, '(n==1 ? 0 : n==2 ? 1 : 2)'),
    # Galician - From Pootle's PO's
    'gl': (2, '(n != 1)'),
    # Hausa - From Pootle's PO's
    'ha': (2, '(n != 1)'),
    # Hebrew
    'he': (2, '(n != 1)'),
    # Hindi - From Pootle's PO's
    'hi': (2, '(n != 1)'),
    # Croatian
    'hr': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Hungarian
    'hu': (1, '0'),
    # Armenian - From Pootle's PO's
    'hy': (1, '0'),
    # Icelandic - From Pootle's PO's
    'is': (2, '(n != 1)'),
    # Italian
    'it': (2, '(n != 1)'),
    # Japanese
    'ja': (1, '0'),
    # Georgian - From Pootle's PO's
    'ka': (1, '0'),
    # Kongo - From Pootle's PO's
    'kg': (2, '(n != 1)'),
    # Khmer - From Pootle's PO's
    'km': (1, '0'),
    # Korean
    'ko': (1, '0'),
    # Kurdish - From Pootle's PO's
    'ku': (2, '(n != 1)'),
    # Lao - Another member of the Tai language family, like Thai.
    'lo': (1, '0'),
    # Lithuanian
    'lt': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Latvian
    'lv': (3, '(n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 : 2)'),
    # Maltese - From Pootle's PO's
    'mt': (4, '(n==1 ? 0 : n==0 || ( n%100>1 && n%100<11) ? 1 : (n%100>10 && n%100<20 ) ? 2 : 3)'),
    # Norwegian Bokmål
    'nb': (2, '(n != 1)'),
    # Dutch
    'nl': (2, '(n != 1)'),
    # Norwegian Nynorsk
    'nn': (2, '(n != 1)'),
    # Norwegian
    'no': (2, '(n != 1)'),
    # Punjabi - From Pootle's PO's
    'pa': (2, '(n != 1)'),
    # Polish
    'pl': (3, '(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Portuguese
    'pt': (2, '(n != 1)'),
    # Brazilian
    'pt_BR': (2, '(n > 1)'),
    # Romanian - From Pootle's PO's
    'ro': (3, '(n==1 ? 0 : (n==0 || (n%100 > 0 && n%100 < 20)) ? 1 : 2)'),
    # Russian
    'ru': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Slovak
    'sk': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Slovenian
    'sl': (4, '(n%100==1 ? 0 : n%100==2 ? 1 : n%100==3 || n%100==4 ? 2 : 3)'),
    # Serbian - From Pootle's PO's
    'sr': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Southern Sotho - From Pootle's PO's
    'st': (2, '(n != 1)'),
    # Swedish
    'sv': (2, '(n != 1)'),
    # Thai
    'th': (1, '0'),
    # Turkish
    'tr': (1, '0'),
    # Ukrainian
    'uk': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Venda - From Pootle's PO's
    've': (2, '(n != 1)'),
    # Vietnamese - From Pootle's PO's
    'vi': (1, '0'),
    # Xhosa - From Pootle's PO's
    'xh': (2, '(n != 1)'),
    # Chinese - From Pootle's PO's
    'zh_CN': (1, '0'),
    'zh_HK': (1, '0'),
    'zh_TW': (1, '0'),
}


DEFAULT_PLURAL = (2, '(n != 1)')


class _PluralTuple(tuple):
    """A tuple with plural information."""

    __slots__ = ()
    num_plurals = property(itemgetter(0), doc="""
    The number of plurals used by the locale.""")
    plural_expr = property(itemgetter(1), doc="""
    The plural expression used by the locale.""")
    plural_forms = property(lambda x: 'npurals=%s; plural=%s' % x, doc="""
    The plural expression used by the catalog or locale.""")

    def __str__(self):
        return self.plural_forms


def get_plural(locale=LC_CTYPE):
    """A tuple with the information catalogs need to perform proper
    pluralization.  The first item of the tuple is the number of plural
    forms, the second the plural expression.

    >>> get_plural(locale='en')
    (2, '(n != 1)')
    >>> get_plural(locale='ga')
    (3, '(n==1 ? 0 : n==2 ? 1 : 2)')

    The object returned is a special tuple with additional members:

    >>> tup = get_plural("ja")
    >>> tup.num_plurals
    1
    >>> tup.plural_expr
    '0'
    >>> tup.plural_forms
    'npurals=1; plural=0'

    Converting the tuple into a string prints the plural forms for a
    gettext catalog:

    >>> str(tup)
    'npurals=1; plural=0'
    """
    locale = Locale.parse(locale)
    try:
        tup = PLURALS[str(locale)]
    except KeyError:
        try:
            tup = PLURALS[locale.language]
        except KeyError:
            tup = DEFAULT_PLURAL
    return _PluralTuple(tup)

########NEW FILE########
__FILENAME__ = pofile
# -*- coding: utf-8 -*-
"""
    babel.messages.pofile
    ~~~~~~~~~~~~~~~~~~~~~

    Reading and writing of files in the ``gettext`` PO (portable object)
    format.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import os
import re

from babel.messages.catalog import Catalog, Message
from babel.util import wraptext
from babel._compat import text_type


def unescape(string):
    r"""Reverse `escape` the given string.

    >>> print unescape('"Say:\\n  \\"hello, world!\\"\\n"')
    Say:
      "hello, world!"
    <BLANKLINE>

    :param string: the string to unescape
    """
    def replace_escapes(match):
        m = match.group(1)
        if m == 'n':
            return '\n'
        elif m == 't':
            return '\t'
        elif m == 'r':
            return '\r'
        # m is \ or "
        return m
    return re.compile(r'\\([\\trn"])').sub(replace_escapes, string[1:-1])


def denormalize(string):
    r"""Reverse the normalization done by the `normalize` function.

    >>> print denormalize(r'''""
    ... "Say:\n"
    ... "  \"hello, world!\"\n"''')
    Say:
      "hello, world!"
    <BLANKLINE>

    >>> print denormalize(r'''""
    ... "Say:\n"
    ... "  \"Lorem ipsum dolor sit "
    ... "amet, consectetur adipisicing"
    ... " elit, \"\n"''')
    Say:
      "Lorem ipsum dolor sit amet, consectetur adipisicing elit, "
    <BLANKLINE>

    :param string: the string to denormalize
    """
    if '\n' in string:
        escaped_lines = string.splitlines()
        if string.startswith('""'):
            escaped_lines = escaped_lines[1:]
        lines = map(unescape, escaped_lines)
        return ''.join(lines)
    else:
        return unescape(string)


def read_po(fileobj, locale=None, domain=None, ignore_obsolete=False, charset=None):
    """Read messages from a ``gettext`` PO (portable object) file from the given
    file-like object and return a `Catalog`.

    >>> from datetime import datetime
    >>> from StringIO import StringIO
    >>> buf = StringIO('''
    ... #: main.py:1
    ... #, fuzzy, python-format
    ... msgid "foo %(name)s"
    ... msgstr "quux %(name)s"
    ...
    ... # A user comment
    ... #. An auto comment
    ... #: main.py:3
    ... msgid "bar"
    ... msgid_plural "baz"
    ... msgstr[0] "bar"
    ... msgstr[1] "baaz"
    ... ''')
    >>> catalog = read_po(buf)
    >>> catalog.revision_date = datetime(2007, 04, 01)

    >>> for message in catalog:
    ...     if message.id:
    ...         print (message.id, message.string)
    ...         print ' ', (message.locations, message.flags)
    ...         print ' ', (message.user_comments, message.auto_comments)
    (u'foo %(name)s', u'quux %(name)s')
      ([(u'main.py', 1)], set([u'fuzzy', u'python-format']))
      ([], [])
    ((u'bar', u'baz'), (u'bar', u'baaz'))
      ([(u'main.py', 3)], set([]))
      ([u'A user comment'], [u'An auto comment'])

    .. versionadded:: 1.0
       Added support for explicit charset argument.

    :param fileobj: the file-like object to read the PO file from
    :param locale: the locale identifier or `Locale` object, or `None`
                   if the catalog is not bound to a locale (which basically
                   means it's a template)
    :param domain: the message domain
    :param ignore_obsolete: whether to ignore obsolete messages in the input
    :param charset: the character set of the catalog.
    """
    catalog = Catalog(locale=locale, domain=domain, charset=charset)

    counter = [0]
    offset = [0]
    messages = []
    translations = []
    locations = []
    flags = []
    user_comments = []
    auto_comments = []
    obsolete = [False]
    context = []
    in_msgid = [False]
    in_msgstr = [False]
    in_msgctxt = [False]

    def _add_message():
        translations.sort()
        if len(messages) > 1:
            msgid = tuple([denormalize(m) for m in messages])
        else:
            msgid = denormalize(messages[0])
        if isinstance(msgid, (list, tuple)):
            string = []
            for idx in range(catalog.num_plurals):
                try:
                    string.append(translations[idx])
                except IndexError:
                    string.append((idx, ''))
            string = tuple([denormalize(t[1]) for t in string])
        else:
            string = denormalize(translations[0][1])
        if context:
            msgctxt = denormalize('\n'.join(context))
        else:
            msgctxt = None
        message = Message(msgid, string, list(locations), set(flags),
                          auto_comments, user_comments, lineno=offset[0] + 1,
                          context=msgctxt)
        if obsolete[0]:
            if not ignore_obsolete:
                catalog.obsolete[msgid] = message
        else:
            catalog[msgid] = message
        del messages[:]; del translations[:]; del context[:]; del locations[:];
        del flags[:]; del auto_comments[:]; del user_comments[:];
        obsolete[0] = False
        counter[0] += 1

    def _process_message_line(lineno, line):
        if line.startswith('msgid_plural'):
            in_msgid[0] = True
            msg = line[12:].lstrip()
            messages.append(msg)
        elif line.startswith('msgid'):
            in_msgid[0] = True
            offset[0] = lineno
            txt = line[5:].lstrip()
            if messages:
                _add_message()
            messages.append(txt)
        elif line.startswith('msgstr'):
            in_msgid[0] = False
            in_msgstr[0] = True
            msg = line[6:].lstrip()
            if msg.startswith('['):
                idx, msg = msg[1:].split(']', 1)
                translations.append([int(idx), msg.lstrip()])
            else:
                translations.append([0, msg])
        elif line.startswith('msgctxt'):
            if messages:
                _add_message()
            in_msgid[0] = in_msgstr[0] = False
            context.append(line[7:].lstrip())
        elif line.startswith('"'):
            if in_msgid[0]:
                messages[-1] += u'\n' + line.rstrip()
            elif in_msgstr[0]:
                translations[-1][1] += u'\n' + line.rstrip()
            elif in_msgctxt[0]:
                context.append(line.rstrip())

    for lineno, line in enumerate(fileobj.readlines()):
        line = line.strip()
        if not isinstance(line, text_type):
            line = line.decode(catalog.charset)
        if line.startswith('#'):
            in_msgid[0] = in_msgstr[0] = False
            if messages and translations:
                _add_message()
            if line[1:].startswith(':'):
                for location in line[2:].lstrip().split():
                    pos = location.rfind(':')
                    if pos >= 0:
                        try:
                            lineno = int(location[pos + 1:])
                        except ValueError:
                            continue
                        locations.append((location[:pos], lineno))
            elif line[1:].startswith(','):
                for flag in line[2:].lstrip().split(','):
                    flags.append(flag.strip())
            elif line[1:].startswith('~'):
                obsolete[0] = True
                _process_message_line(lineno, line[2:].lstrip())
            elif line[1:].startswith('.'):
                # These are called auto-comments
                comment = line[2:].strip()
                if comment: # Just check that we're not adding empty comments
                    auto_comments.append(comment)
            else:
                # These are called user comments
                user_comments.append(line[1:].strip())
        else:
            _process_message_line(lineno, line)

    if messages:
        _add_message()

    # No actual messages found, but there was some info in comments, from which
    # we'll construct an empty header message
    elif not counter[0] and (flags or user_comments or auto_comments):
        messages.append(u'')
        translations.append([0, u''])
        _add_message()

    return catalog


WORD_SEP = re.compile('('
    r'\s+|'                                 # any whitespace
    r'[^\s\w]*\w+[a-zA-Z]-(?=\w+[a-zA-Z])|' # hyphenated words
    r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w)'   # em-dash
')')


def escape(string):
    r"""Escape the given string so that it can be included in double-quoted
    strings in ``PO`` files.

    >>> escape('''Say:
    ...   "hello, world!"
    ... ''')
    '"Say:\\n  \\"hello, world!\\"\\n"'

    :param string: the string to escape
    """
    return '"%s"' % string.replace('\\', '\\\\') \
                          .replace('\t', '\\t') \
                          .replace('\r', '\\r') \
                          .replace('\n', '\\n') \
                          .replace('\"', '\\"')


def normalize(string, prefix='', width=76):
    r"""Convert a string into a format that is appropriate for .po files.

    >>> print normalize('''Say:
    ...   "hello, world!"
    ... ''', width=None)
    ""
    "Say:\n"
    "  \"hello, world!\"\n"

    >>> print normalize('''Say:
    ...   "Lorem ipsum dolor sit amet, consectetur adipisicing elit, "
    ... ''', width=32)
    ""
    "Say:\n"
    "  \"Lorem ipsum dolor sit "
    "amet, consectetur adipisicing"
    " elit, \"\n"

    :param string: the string to normalize
    :param prefix: a string that should be prepended to every line
    :param width: the maximum line width; use `None`, 0, or a negative number
                  to completely disable line wrapping
    """
    if width and width > 0:
        prefixlen = len(prefix)
        lines = []
        for line in string.splitlines(True):
            if len(escape(line)) + prefixlen > width:
                chunks = WORD_SEP.split(line)
                chunks.reverse()
                while chunks:
                    buf = []
                    size = 2
                    while chunks:
                        l = len(escape(chunks[-1])) - 2 + prefixlen
                        if size + l < width:
                            buf.append(chunks.pop())
                            size += l
                        else:
                            if not buf:
                                # handle long chunks by putting them on a
                                # separate line
                                buf.append(chunks.pop())
                            break
                    lines.append(u''.join(buf))
            else:
                lines.append(line)
    else:
        lines = string.splitlines(True)

    if len(lines) <= 1:
        return escape(string)

    # Remove empty trailing line
    if lines and not lines[-1]:
        del lines[-1]
        lines[-1] += '\n'
    return u'""\n' + u'\n'.join([(prefix + escape(l)) for l in lines])


def write_po(fileobj, catalog, width=76, no_location=False, omit_header=False,
             sort_output=False, sort_by_file=False, ignore_obsolete=False,
             include_previous=False):
    r"""Write a ``gettext`` PO (portable object) template file for a given
    message catalog to the provided file-like object.

    >>> catalog = Catalog()
    >>> catalog.add(u'foo %(name)s', locations=[('main.py', 1)],
    ...             flags=('fuzzy',))
    <Message...>
    >>> catalog.add((u'bar', u'baz'), locations=[('main.py', 3)])
    <Message...>
    >>> from io import BytesIO
    >>> buf = BytesIO()
    >>> write_po(buf, catalog, omit_header=True)
    >>> print buf.getvalue()
    #: main.py:1
    #, fuzzy, python-format
    msgid "foo %(name)s"
    msgstr ""
    <BLANKLINE>
    #: main.py:3
    msgid "bar"
    msgid_plural "baz"
    msgstr[0] ""
    msgstr[1] ""
    <BLANKLINE>
    <BLANKLINE>

    :param fileobj: the file-like object to write to
    :param catalog: the `Catalog` instance
    :param width: the maximum line width for the generated output; use `None`,
                  0, or a negative number to completely disable line wrapping
    :param no_location: do not emit a location comment for every message
    :param omit_header: do not include the ``msgid ""`` entry at the top of the
                        output
    :param sort_output: whether to sort the messages in the output by msgid
    :param sort_by_file: whether to sort the messages in the output by their
                         locations
    :param ignore_obsolete: whether to ignore obsolete messages and not include
                            them in the output; by default they are included as
                            comments
    :param include_previous: include the old msgid as a comment when
                             updating the catalog
    """
    def _normalize(key, prefix=''):
        return normalize(key, prefix=prefix, width=width)

    def _write(text):
        if isinstance(text, text_type):
            text = text.encode(catalog.charset, 'backslashreplace')
        fileobj.write(text)

    def _write_comment(comment, prefix=''):
        # xgettext always wraps comments even if --no-wrap is passed;
        # provide the same behaviour
        if width and width > 0:
            _width = width
        else:
            _width = 76
        for line in wraptext(comment, _width):
            _write('#%s %s\n' % (prefix, line.strip()))

    def _write_message(message, prefix=''):
        if isinstance(message.id, (list, tuple)):
            if message.context:
                _write('%smsgctxt %s\n' % (prefix,
                                           _normalize(message.context, prefix)))
            _write('%smsgid %s\n' % (prefix, _normalize(message.id[0], prefix)))
            _write('%smsgid_plural %s\n' % (
                prefix, _normalize(message.id[1], prefix)
            ))

            for idx in range(catalog.num_plurals):
                try:
                    string = message.string[idx]
                except IndexError:
                    string = ''
                _write('%smsgstr[%d] %s\n' % (
                    prefix, idx, _normalize(string, prefix)
                ))
        else:
            if message.context:
                _write('%smsgctxt %s\n' % (prefix,
                                           _normalize(message.context, prefix)))
            _write('%smsgid %s\n' % (prefix, _normalize(message.id, prefix)))
            _write('%smsgstr %s\n' % (
                prefix, _normalize(message.string or '', prefix)
            ))

    messages = list(catalog)
    if sort_output:
        messages.sort()
    elif sort_by_file:
        messages.sort(lambda x,y: cmp(x.locations, y.locations))

    for message in messages:
        if not message.id: # This is the header "message"
            if omit_header:
                continue
            comment_header = catalog.header_comment
            if width and width > 0:
                lines = []
                for line in comment_header.splitlines():
                    lines += wraptext(line, width=width,
                                      subsequent_indent='# ')
                comment_header = u'\n'.join(lines)
            _write(comment_header + u'\n')

        for comment in message.user_comments:
            _write_comment(comment)
        for comment in message.auto_comments:
            _write_comment(comment, prefix='.')

        if not no_location:
            locs = u' '.join([u'%s:%d' % (filename.replace(os.sep, '/'), lineno)
                              for filename, lineno in message.locations])
            _write_comment(locs, prefix=':')
        if message.flags:
            _write('#%s\n' % ', '.join([''] + sorted(message.flags)))

        if message.previous_id and include_previous:
            _write_comment('msgid %s' % _normalize(message.previous_id[0]),
                           prefix='|')
            if len(message.previous_id) > 1:
                _write_comment('msgid_plural %s' % _normalize(
                    message.previous_id[1]
                ), prefix='|')

        _write_message(message)
        _write('\n')

    if not ignore_obsolete:
        for message in catalog.obsolete.values():
            for comment in message.user_comments:
                _write_comment(comment)
            _write_message(message, prefix='#~ ')
            _write('\n')

########NEW FILE########
__FILENAME__ = numbers
# -*- coding: utf-8 -*-
"""
    babel.numbers
    ~~~~~~~~~~~~~

    Locale dependent formatting and parsing of numeric data.

    The default locale for the functions in this module is determined by the
    following environment variables, in that order:

     * ``LC_NUMERIC``,
     * ``LC_ALL``, and
     * ``LANG``

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""
# TODO:
#  Padding and rounding increments in pattern:
#  - http://www.unicode.org/reports/tr35/ (Appendix G.6)
from decimal import Decimal, InvalidOperation
import math
import re
from datetime import date as date_, datetime as datetime_

from babel.core import default_locale, Locale, get_global
from babel._compat import range_type


LC_NUMERIC = default_locale('LC_NUMERIC')


def get_currency_name(currency, count=None, locale=LC_NUMERIC):
    """Return the name used by the locale for the specified currency.

    >>> get_currency_name('USD', locale='en_US')
    u'US Dollar'
    
    .. versionadded:: 0.9.4

    :param currency: the currency code
    :param count: the optional count.  If provided the currency name
                  will be pluralized to that number if possible.
    :param locale: the `Locale` object or locale identifier
    """
    loc = Locale.parse(locale)
    if count is not None:
        plural_form = loc.plural_form(count)
        plural_names = loc._data['currency_names_plural']
        if currency in plural_names:
            return plural_names[currency][plural_form]
    return loc.currencies.get(currency, currency)


def get_currency_symbol(currency, locale=LC_NUMERIC):
    """Return the symbol used by the locale for the specified currency.

    >>> get_currency_symbol('USD', locale='en_US')
    u'$'

    :param currency: the currency code
    :param locale: the `Locale` object or locale identifier
    """
    return Locale.parse(locale).currency_symbols.get(currency, currency)


def get_territory_currencies(territory, start_date=None, end_date=None,
                             tender=True, non_tender=False,
                             include_details=False):
    """Returns the list of currencies for the given territory that are valid for
    the given date range.  In addition to that the currency database
    distinguishes between tender and non-tender currencies.  By default only
    tender currencies are returned.

    The return value is a list of all currencies roughly ordered by the time
    of when the currency became active.  The longer the currency is being in
    use the more to the left of the list it will be.

    The start date defaults to today.  If no end date is given it will be the
    same as the start date.  Otherwise a range can be defined.  For instance
    this can be used to find the currencies in use in Austria between 1995 and
    2011:

    >>> from datetime import date
    >>> get_territory_currencies('AT', date(1995, 1, 1), date(2011, 1, 1))
    ['ATS', 'EUR']

    Likewise it's also possible to find all the currencies in use on a
    single date:

    >>> get_territory_currencies('AT', date(1995, 1, 1))
    ['ATS']
    >>> get_territory_currencies('AT', date(2011, 1, 1))
    ['EUR']

    By default the return value only includes tender currencies.  This
    however can be changed:

    >>> get_territory_currencies('US')
    ['USD']
    >>> get_territory_currencies('US', tender=False, non_tender=True)
    ['USN', 'USS']

    .. versionadded:: 2.0

    :param territory: the name of the territory to find the currency fo
    :param start_date: the start date.  If not given today is assumed.
    :param end_date: the end date.  If not given the start date is assumed.
    :param tender: controls whether tender currencies should be included.
    :param non_tender: controls whether non-tender currencies should be
                       included.
    :param include_details: if set to `True`, instead of returning currency
                            codes the return value will be dictionaries
                            with detail information.  In that case each
                            dictionary will have the keys ``'currency'``,
                            ``'from'``, ``'to'``, and ``'tender'``.
    """
    currencies = get_global('territory_currencies')
    if start_date is None:
        start_date = date_.today()
    elif isinstance(start_date, datetime_):
        start_date = start_date.date()
    if end_date is None:
        end_date = start_date
    elif isinstance(end_date, datetime_):
        end_date = end_date.date()

    curs = currencies.get(territory.upper(), ())
    # TODO: validate that the territory exists

    def _is_active(start, end):
        return (start is None or start <= end_date) and \
               (end is None or end >= start_date)

    result = []
    for currency_code, start, end, is_tender in curs:
        if ((is_tender and tender) or \
            (not is_tender and non_tender)) and _is_active(start, end):
            if include_details:
                result.append({
                    'currency': currency_code,
                    'from': start,
                    'to': end,
                    'tender': is_tender,
                })
            else:
                result.append(currency_code)

    return result


def get_decimal_symbol(locale=LC_NUMERIC):
    """Return the symbol used by the locale to separate decimal fractions.

    >>> get_decimal_symbol('en_US')
    u'.'

    :param locale: the `Locale` object or locale identifier
    """
    return Locale.parse(locale).number_symbols.get('decimal', u'.')


def get_plus_sign_symbol(locale=LC_NUMERIC):
    """Return the plus sign symbol used by the current locale.

    >>> get_plus_sign_symbol('en_US')
    u'+'

    :param locale: the `Locale` object or locale identifier
    """
    return Locale.parse(locale).number_symbols.get('plusSign', u'+')


def get_minus_sign_symbol(locale=LC_NUMERIC):
    """Return the plus sign symbol used by the current locale.

    >>> get_minus_sign_symbol('en_US')
    u'-'

    :param locale: the `Locale` object or locale identifier
    """
    return Locale.parse(locale).number_symbols.get('minusSign', u'-')


def get_exponential_symbol(locale=LC_NUMERIC):
    """Return the symbol used by the locale to separate mantissa and exponent.

    >>> get_exponential_symbol('en_US')
    u'E'

    :param locale: the `Locale` object or locale identifier
    """
    return Locale.parse(locale).number_symbols.get('exponential', u'E')


def get_group_symbol(locale=LC_NUMERIC):
    """Return the symbol used by the locale to separate groups of thousands.

    >>> get_group_symbol('en_US')
    u','

    :param locale: the `Locale` object or locale identifier
    """
    return Locale.parse(locale).number_symbols.get('group', u',')


def format_number(number, locale=LC_NUMERIC):
    u"""Return the given number formatted for a specific locale.

    >>> format_number(1099, locale='en_US')
    u'1,099'
    >>> format_number(1099, locale='de_DE')
    u'1.099'


    :param number: the number to format
    :param locale: the `Locale` object or locale identifier
    """
    # Do we really need this one?
    return format_decimal(number, locale=locale)


def format_decimal(number, format=None, locale=LC_NUMERIC):
    u"""Return the given decimal number formatted for a specific locale.

    >>> format_decimal(1.2345, locale='en_US')
    u'1.234'
    >>> format_decimal(1.2346, locale='en_US')
    u'1.235'
    >>> format_decimal(-1.2346, locale='en_US')
    u'-1.235'
    >>> format_decimal(1.2345, locale='sv_SE')
    u'1,234'
    >>> format_decimal(1.2345, locale='de')
    u'1,234'

    The appropriate thousands grouping and the decimal separator are used for
    each locale:

    >>> format_decimal(12345.5, locale='en_US')
    u'12,345.5'

    :param number: the number to format
    :param format:
    :param locale: the `Locale` object or locale identifier
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.decimal_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale)


def format_currency(number, currency, format=None, locale=LC_NUMERIC):
    u"""Return formatted currency value.

    >>> format_currency(1099.98, 'USD', locale='en_US')
    u'$1,099.98'
    >>> format_currency(1099.98, 'USD', locale='es_CO')
    u'1.099,98\\xa0US$'
    >>> format_currency(1099.98, 'EUR', locale='de_DE')
    u'1.099,98\\xa0\\u20ac'

    The pattern can also be specified explicitly.  The currency is
    placed with the '¤' sign.  As the sign gets repeated the format
    expands (¤ being the symbol, ¤¤ is the currency abbreviation and
    ¤¤¤ is the full name of the currency):

    >>> format_currency(1099.98, 'EUR', u'\xa4\xa4 #,##0.00', locale='en_US')
    u'EUR 1,099.98'
    >>> format_currency(1099.98, 'EUR', u'#,##0.00 \xa4\xa4\xa4', locale='en_US')
    u'1,099.98 euros'

    :param number: the number to format
    :param currency: the currency code
    :param locale: the `Locale` object or locale identifier
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.currency_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale, currency=currency)


def format_percent(number, format=None, locale=LC_NUMERIC):
    """Return formatted percent value for a specific locale.

    >>> format_percent(0.34, locale='en_US')
    u'34%'
    >>> format_percent(25.1234, locale='en_US')
    u'2,512%'
    >>> format_percent(25.1234, locale='sv_SE')
    u'2\\xa0512\\xa0%'

    The format pattern can also be specified explicitly:

    >>> format_percent(25.1234, u'#,##0\u2030', locale='en_US')
    u'25,123\u2030'

    :param number: the percent number to format
    :param format:
    :param locale: the `Locale` object or locale identifier
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.percent_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale)


def format_scientific(number, format=None, locale=LC_NUMERIC):
    """Return value formatted in scientific notation for a specific locale.

    >>> format_scientific(10000, locale='en_US')
    u'1E4'

    The format pattern can also be specified explicitly:

    >>> format_scientific(1234567, u'##0E00', locale='en_US')
    u'1.23E06'

    :param number: the number to format
    :param format:
    :param locale: the `Locale` object or locale identifier
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.scientific_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale)


class NumberFormatError(ValueError):
    """Exception raised when a string cannot be parsed into a number."""


def parse_number(string, locale=LC_NUMERIC):
    """Parse localized number string into an integer.

    >>> parse_number('1,099', locale='en_US')
    1099
    >>> parse_number('1.099', locale='de_DE')
    1099

    When the given string cannot be parsed, an exception is raised:

    >>> parse_number('1.099,98', locale='de')
    Traceback (most recent call last):
        ...
    NumberFormatError: '1.099,98' is not a valid number

    :param string: the string to parse
    :param locale: the `Locale` object or locale identifier
    :return: the parsed number
    :raise `NumberFormatError`: if the string can not be converted to a number
    """
    try:
        return int(string.replace(get_group_symbol(locale), ''))
    except ValueError:
        raise NumberFormatError('%r is not a valid number' % string)


def parse_decimal(string, locale=LC_NUMERIC):
    """Parse localized decimal string into a decimal.

    >>> parse_decimal('1,099.98', locale='en_US')
    Decimal('1099.98')
    >>> parse_decimal('1.099,98', locale='de')
    Decimal('1099.98')

    When the given string cannot be parsed, an exception is raised:

    >>> parse_decimal('2,109,998', locale='de')
    Traceback (most recent call last):
        ...
    NumberFormatError: '2,109,998' is not a valid decimal number

    :param string: the string to parse
    :param locale: the `Locale` object or locale identifier
    :raise NumberFormatError: if the string can not be converted to a
                              decimal number
    """
    locale = Locale.parse(locale)
    try:
        return Decimal(string.replace(get_group_symbol(locale), '')
                           .replace(get_decimal_symbol(locale), '.'))
    except InvalidOperation:
        raise NumberFormatError('%r is not a valid decimal number' % string)


PREFIX_END = r'[^0-9@#.,]'
NUMBER_TOKEN = r'[0-9@#.,E+]'

PREFIX_PATTERN = r"(?P<prefix>(?:'[^']*'|%s)*)" % PREFIX_END
NUMBER_PATTERN = r"(?P<number>%s+)" % NUMBER_TOKEN
SUFFIX_PATTERN = r"(?P<suffix>.*)"

number_re = re.compile(r"%s%s%s" % (PREFIX_PATTERN, NUMBER_PATTERN,
                                    SUFFIX_PATTERN))

def split_number(value):
    """Convert a number into a (intasstring, fractionasstring) tuple"""
    if isinstance(value, Decimal):
        # NB can't just do text = str(value) as str repr of Decimal may be
        # in scientific notation, e.g. for small numbers.

        sign, digits, exp = value.as_tuple()
        # build list of digits in reverse order, then reverse+join
        # as per http://docs.python.org/library/decimal.html#recipes
        int_part = []
        frac_part = []

        digits = list(map(str, digits))

        # get figures after decimal point
        for i in range(-exp):
            # add digit if available, else 0
            if digits:
                frac_part.append(digits.pop())
            else:
                frac_part.append('0')

        # add in some zeroes...
        for i in range(exp):
            int_part.append('0')

        # and the rest
        while digits:
            int_part.append(digits.pop())

        # if < 1, int_part must be set to '0'
        if len(int_part) == 0:
            int_part = '0',

        if sign:
            int_part.append('-')

        return ''.join(reversed(int_part)), ''.join(reversed(frac_part))
    text = ('%.9f' % value).rstrip('0')
    if '.' in text:
        a, b = text.split('.', 1)
        if b == '0':
            b = ''
    else:
        a, b = text, ''
    return a, b


def bankersround(value, ndigits=0):
    """Round a number to a given precision.

    Works like round() except that the round-half-even (banker's rounding)
    algorithm is used instead of round-half-up.

    >>> bankersround(5.5, 0)
    6.0
    >>> bankersround(6.5, 0)
    6.0
    >>> bankersround(-6.5, 0)
    -6.0
    >>> bankersround(1234.0, -2)
    1200.0
    """
    sign = int(value < 0) and -1 or 1
    value = abs(value)
    a, b = split_number(value)
    digits = a + b
    add = 0
    i = len(a) + ndigits
    if i < 0 or i >= len(digits):
        pass
    elif digits[i] > '5':
        add = 1
    elif digits[i] == '5' and digits[i-1] in '13579':
        add = 1
    elif digits[i] == '5':     # previous digit is even
        # We round up unless all following digits are zero.
        for j in range_type(i + 1, len(digits)):
            if digits[j] != '0':
                add = 1
                break

    scale = 10**ndigits
    if isinstance(value, Decimal):
        return Decimal(int(value * scale + add)) / scale * sign
    else:
        return float(int(value * scale + add)) / scale * sign


def parse_grouping(p):
    """Parse primary and secondary digit grouping

    >>> parse_grouping('##')
    (1000, 1000)
    >>> parse_grouping('#,###')
    (3, 3)
    >>> parse_grouping('#,####,###')
    (3, 4)
    """
    width = len(p)
    g1 = p.rfind(',')
    if g1 == -1:
        return 1000, 1000
    g1 = width - g1 - 1
    g2 = p[:-g1 - 1].rfind(',')
    if g2 == -1:
        return g1, g1
    g2 = width - g1 - g2 - 2
    return g1, g2


def parse_pattern(pattern):
    """Parse number format patterns"""
    if isinstance(pattern, NumberPattern):
        return pattern

    def _match_number(pattern):
        rv = number_re.search(pattern)
        if rv is None:
            raise ValueError('Invalid number pattern %r' % pattern)
        return rv.groups()

    # Do we have a negative subpattern?
    if ';' in pattern:
        pattern, neg_pattern = pattern.split(';', 1)
        pos_prefix, number, pos_suffix = _match_number(pattern)
        neg_prefix, _, neg_suffix = _match_number(neg_pattern)
    else:
        pos_prefix, number, pos_suffix = _match_number(pattern)
        neg_prefix = '-' + pos_prefix
        neg_suffix = pos_suffix
    if 'E' in number:
        number, exp = number.split('E', 1)
    else:
        exp = None
    if '@' in number:
        if '.' in number and '0' in number:
            raise ValueError('Significant digit patterns can not contain '
                             '"@" or "0"')
    if '.' in number:
        integer, fraction = number.rsplit('.', 1)
    else:
        integer = number
        fraction = ''

    def parse_precision(p):
        """Calculate the min and max allowed digits"""
        min = max = 0
        for c in p:
            if c in '@0':
                min += 1
                max += 1
            elif c == '#':
                max += 1
            elif c == ',':
                continue
            else:
                break
        return min, max

    int_prec = parse_precision(integer)
    frac_prec = parse_precision(fraction)
    if exp:
        frac_prec = parse_precision(integer+fraction)
        exp_plus = exp.startswith('+')
        exp = exp.lstrip('+')
        exp_prec = parse_precision(exp)
    else:
        exp_plus = None
        exp_prec = None
    grouping = parse_grouping(integer)
    return NumberPattern(pattern, (pos_prefix, neg_prefix),
                         (pos_suffix, neg_suffix), grouping,
                         int_prec, frac_prec,
                         exp_prec, exp_plus)


class NumberPattern(object):

    def __init__(self, pattern, prefix, suffix, grouping,
                 int_prec, frac_prec, exp_prec, exp_plus):
        self.pattern = pattern
        self.prefix = prefix
        self.suffix = suffix
        self.grouping = grouping
        self.int_prec = int_prec
        self.frac_prec = frac_prec
        self.exp_prec = exp_prec
        self.exp_plus = exp_plus
        if '%' in ''.join(self.prefix + self.suffix):
            self.scale = 100
        elif u'‰' in ''.join(self.prefix + self.suffix):
            self.scale = 1000
        else:
            self.scale = 1

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.pattern)

    def apply(self, value, locale, currency=None):
        if isinstance(value, float):
            value = Decimal(str(value))
        value *= self.scale
        is_negative = int(value < 0)
        if self.exp_prec: # Scientific notation
            value = abs(value)
            if value:
                exp = int(math.floor(math.log(value, 10)))
            else:
                exp = 0
            # Minimum number of integer digits
            if self.int_prec[0] == self.int_prec[1]:
                exp -= self.int_prec[0] - 1
            # Exponent grouping
            elif self.int_prec[1]:
                exp = int(exp / self.int_prec[1]) * self.int_prec[1]
            if not isinstance(value, Decimal):
                value = float(value)
            if exp < 0:
                value = value * 10**(-exp)
            else:
                value = value / 10**exp
            exp_sign = ''
            if exp < 0:
                exp_sign = get_minus_sign_symbol(locale)
            elif self.exp_plus:
                exp_sign = get_plus_sign_symbol(locale)
            exp = abs(exp)
            number = u'%s%s%s%s' % \
                 (self._format_sigdig(value, self.frac_prec[0],
                                     self.frac_prec[1]),
                  get_exponential_symbol(locale),  exp_sign,
                  self._format_int(str(exp), self.exp_prec[0],
                                   self.exp_prec[1], locale))
        elif '@' in self.pattern: # Is it a siginificant digits pattern?
            text = self._format_sigdig(abs(value),
                                      self.int_prec[0],
                                      self.int_prec[1])
            if '.' in text:
                a, b = text.split('.')
                a = self._format_int(a, 0, 1000, locale)
                if b:
                    b = get_decimal_symbol(locale) + b
                number = a + b
            else:
                number = self._format_int(text, 0, 1000, locale)
        else: # A normal number pattern
            a, b = split_number(bankersround(abs(value),
                                             self.frac_prec[1]))
            b = b or '0'
            a = self._format_int(a, self.int_prec[0],
                                 self.int_prec[1], locale)
            b = self._format_frac(b, locale)
            number = a + b
        retval = u'%s%s%s' % (self.prefix[is_negative], number,
                                self.suffix[is_negative])
        if u'¤' in retval:
            retval = retval.replace(u'¤¤¤',
                get_currency_name(currency, value, locale))
            retval = retval.replace(u'¤¤', currency.upper())
            retval = retval.replace(u'¤', get_currency_symbol(currency, locale))
        return retval

    def _format_sigdig(self, value, min, max):
        """Convert value to a string.

        The resulting string will contain between (min, max) number of
        significant digits.
        """
        a, b = split_number(value)
        ndecimals = len(a)
        if a == '0' and b != '':
            ndecimals = 0
            while b.startswith('0'):
                b = b[1:]
                ndecimals -= 1
        a, b = split_number(bankersround(value, max - ndecimals))
        digits = len((a + b).lstrip('0'))
        if not digits:
            digits = 1
        # Figure out if we need to add any trailing '0':s
        if len(a) >= max and a != '0':
            return a
        if digits < min:
            b += ('0' * (min - digits))
        if b:
            return '%s.%s' % (a, b)
        return a

    def _format_int(self, value, min, max, locale):
        width = len(value)
        if width < min:
            value = '0' * (min - width) + value
        gsize = self.grouping[0]
        ret = ''
        symbol = get_group_symbol(locale)
        while len(value) > gsize:
            ret = symbol + value[-gsize:] + ret
            value = value[:-gsize]
            gsize = self.grouping[1]
        return value + ret

    def _format_frac(self, value, locale):
        min, max = self.frac_prec
        if len(value) < min:
            value += ('0' * (min - len(value)))
        if max == 0 or (min == 0 and int(value) == 0):
            return ''
        width = len(value)
        while len(value) > min and value[-1] == '0':
            value = value[:-1]
        return get_decimal_symbol(locale) + value

########NEW FILE########
__FILENAME__ = plural
# -*- coding: utf-8 -*-
"""
    babel.numbers
    ~~~~~~~~~~~~~

    CLDR Plural support.  See UTS #35.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import re


_plural_tags = ('zero', 'one', 'two', 'few', 'many', 'other')
_fallback_tag = 'other'


class PluralRule(object):
    """Represents a set of language pluralization rules.  The constructor
    accepts a list of (tag, expr) tuples or a dict of CLDR rules. The
    resulting object is callable and accepts one parameter with a positive or
    negative number (both integer and float) for the number that indicates the
    plural form for a string and returns the tag for the format:

    >>> rule = PluralRule({'one': 'n is 1'})
    >>> rule(1)
    'one'
    >>> rule(2)
    'other'

    Currently the CLDR defines these tags: zero, one, two, few, many and
    other where other is an implicit default.  Rules should be mutually
    exclusive; for a given numeric value, only one rule should apply (i.e.
    the condition should only be true for one of the plural rule elements.
    """

    __slots__ = ('abstract', '_func')

    def __init__(self, rules):
        """Initialize the rule instance.

        :param rules: a list of ``(tag, expr)``) tuples with the rules
                      conforming to UTS #35 or a dict with the tags as keys
                      and expressions as values.
        :raise RuleError: if the expression is malformed
        """
        if isinstance(rules, dict):
            rules = rules.items()
        found = set()
        self.abstract = []
        for key, expr in sorted(list(rules)):
            if key not in _plural_tags:
                raise ValueError('unknown tag %r' % key)
            elif key in found:
                raise ValueError('tag %r defined twice' % key)
            found.add(key)
            self.abstract.append((key, _Parser(expr).ast))

    def __repr__(self):
        rules = self.rules
        return '<%s %r>' % (
            type(self).__name__,
            ', '.join(['%s: %s' % (tag, rules[tag]) for tag in _plural_tags
                       if tag in rules])
        )

    @classmethod
    def parse(cls, rules):
        """Create a `PluralRule` instance for the given rules.  If the rules
        are a `PluralRule` object, that object is returned.

        :param rules: the rules as list or dict, or a `PluralRule` object
        :raise RuleError: if the expression is malformed
        """
        if isinstance(rules, cls):
            return rules
        return cls(rules)

    @property
    def rules(self):
        """The `PluralRule` as a dict of unicode plural rules.

        >>> rule = PluralRule({'one': 'n is 1'})
        >>> rule.rules
        {'one': 'n is 1'}
        """
        _compile = _UnicodeCompiler().compile
        return dict([(tag, _compile(ast)) for tag, ast in self.abstract])

    tags = property(lambda x: frozenset([i[0] for i in x.abstract]), doc="""
        A set of explicitly defined tags in this rule.  The implicit default
        ``'other'`` rules is not part of this set unless there is an explicit
        rule for it.""")

    def __getstate__(self):
        return self.abstract

    def __setstate__(self, abstract):
        self.abstract = abstract

    def __call__(self, n):
        if not hasattr(self, '_func'):
            self._func = to_python(self)
        return self._func(n)


def to_javascript(rule):
    """Convert a list/dict of rules or a `PluralRule` object into a JavaScript
    function.  This function depends on no external library:

    >>> to_javascript({'one': 'n is 1'})
    "(function(n) { return (n == 1) ? 'one' : 'other'; })"

    Implementation detail: The function generated will probably evaluate
    expressions involved into range operations multiple times.  This has the
    advantage that external helper functions are not required and is not a
    big performance hit for these simple calculations.

    :param rule: the rules as list or dict, or a `PluralRule` object
    :raise RuleError: if the expression is malformed
    """
    to_js = _JavaScriptCompiler().compile
    result = ['(function(n) { return ']
    for tag, ast in PluralRule.parse(rule).abstract:
        result.append('%s ? %r : ' % (to_js(ast), tag))
    result.append('%r; })' % _fallback_tag)
    return ''.join(result)


def to_python(rule):
    """Convert a list/dict of rules or a `PluralRule` object into a regular
    Python function.  This is useful in situations where you need a real
    function and don't are about the actual rule object:

    >>> func = to_python({'one': 'n is 1', 'few': 'n in 2..4'})
    >>> func(1)
    'one'
    >>> func(3)
    'few'
    >>> func = to_python({'one': 'n in 1,11', 'few': 'n in 3..10,13..19'})
    >>> func(11)
    'one'
    >>> func(15)
    'few'

    :param rule: the rules as list or dict, or a `PluralRule` object
    :raise RuleError: if the expression is malformed
    """
    namespace = {
        'IN':       in_range_list,
        'WITHIN':   within_range_list,
        'MOD':      cldr_modulo
    }
    to_python = _PythonCompiler().compile
    result = ['def evaluate(n):']
    for tag, ast in PluralRule.parse(rule).abstract:
        # the str() call is to coerce the tag to the native string.  It's
        # a limited ascii restricted set of tags anyways so that is fine.
        result.append(' if (%s): return %r' % (to_python(ast), str(tag)))
    result.append(' return %r' % _fallback_tag)
    code = compile('\n'.join(result), '<rule>', 'exec')
    eval(code, namespace)
    return namespace['evaluate']


def to_gettext(rule):
    """The plural rule as gettext expression.  The gettext expression is
    technically limited to integers and returns indices rather than tags.

    >>> to_gettext({'one': 'n is 1', 'two': 'n is 2'})
    'nplurals=3; plural=((n == 1) ? 0 : (n == 2) ? 1 : 2)'

    :param rule: the rules as list or dict, or a `PluralRule` object
    :raise RuleError: if the expression is malformed
    """
    rule = PluralRule.parse(rule)

    used_tags = rule.tags | set([_fallback_tag])
    _compile = _GettextCompiler().compile
    _get_index = [tag for tag in _plural_tags if tag in used_tags].index

    result = ['nplurals=%d; plural=(' % len(used_tags)]
    for tag, ast in rule.abstract:
        result.append('%s ? %d : ' % (_compile(ast), _get_index(tag)))
    result.append('%d)' % _get_index(_fallback_tag))
    return ''.join(result)


def in_range_list(num, range_list):
    """Integer range list test.  This is the callback for the "in" operator
    of the UTS #35 pluralization rule language:

    >>> in_range_list(1, [(1, 3)])
    True
    >>> in_range_list(3, [(1, 3)])
    True
    >>> in_range_list(3, [(1, 3), (5, 8)])
    True
    >>> in_range_list(1.2, [(1, 4)])
    False
    >>> in_range_list(10, [(1, 4)])
    False
    >>> in_range_list(10, [(1, 4), (6, 8)])
    False
    """
    return num == int(num) and within_range_list(num, range_list)


def within_range_list(num, range_list):
    """Float range test.  This is the callback for the "within" operator
    of the UTS #35 pluralization rule language:

    >>> within_range_list(1, [(1, 3)])
    True
    >>> within_range_list(1.0, [(1, 3)])
    True
    >>> within_range_list(1.2, [(1, 4)])
    True
    >>> within_range_list(8.8, [(1, 4), (7, 15)])
    True
    >>> within_range_list(10, [(1, 4)])
    False
    >>> within_range_list(10.5, [(1, 4), (20, 30)])
    False
    """
    return any(num >= min_ and num <= max_ for min_, max_ in range_list)


def cldr_modulo(a, b):
    """Javaish modulo.  This modulo operator returns the value with the sign
    of the dividend rather than the divisor like Python does:

    >>> cldr_modulo(-3, 5)
    -3
    >>> cldr_modulo(-3, -5)
    -3
    >>> cldr_modulo(3, 5)
    3
    """
    reverse = 0
    if a < 0:
        a *= -1
        reverse = 1
    if b < 0:
        b *= -1
    rv = a % b
    if reverse:
        rv *= -1
    return rv


class RuleError(Exception):
    """Raised if a rule is malformed."""


class _Parser(object):
    """Internal parser.  This class can translate a single rule into an abstract
    tree of tuples. It implements the following grammar::

        condition     = and_condition ('or' and_condition)*
        and_condition = relation ('and' relation)*
        relation      = is_relation | in_relation | within_relation | 'n' <EOL>
        is_relation   = expr 'is' ('not')? value
        in_relation   = expr ('not')? 'in' range_list
        within_relation = expr ('not')? 'within' range_list
        expr          = 'n' ('mod' value)?
        range_list    = (range | value) (',' range_list)*
        value         = digit+
        digit         = 0|1|2|3|4|5|6|7|8|9
        range         = value'..'value

    - Whitespace can occur between or around any of the above tokens.
    - Rules should be mutually exclusive; for a given numeric value, only one
      rule should apply (i.e. the condition should only be true for one of
      the plural rule elements).
    - The in and within relations can take comma-separated lists, such as:
      'n in 3,5,7..15'.

    The translator parses the expression on instanciation into an attribute
    called `ast`.
    """

    _rules = [
        (None, re.compile(r'\s+(?u)')),
        ('word', re.compile(r'\b(and|or|is|(?:with)?in|not|mod|n)\b')),
        ('value', re.compile(r'\d+')),
        ('comma', re.compile(r',')),
        ('ellipsis', re.compile(r'\.\.'))
    ]

    def __init__(self, string):
        string = string.lower()
        result = []
        pos = 0
        end = len(string)
        while pos < end:
            for tok, rule in self._rules:
                match = rule.match(string, pos)
                if match is not None:
                    pos = match.end()
                    if tok:
                        result.append((tok, match.group()))
                    break
            else:
                raise RuleError('malformed CLDR pluralization rule.  '
                                'Got unexpected %r' % string[pos])
        self.tokens = result[::-1]

        self.ast = self.condition()
        if self.tokens:
            raise RuleError('Expected end of rule, got %r' %
                            self.tokens[-1][1])

    def test(self, type, value=None):
        return self.tokens and self.tokens[-1][0] == type and \
               (value is None or self.tokens[-1][1] == value)

    def skip(self, type, value=None):
        if self.test(type, value):
            return self.tokens.pop()

    def expect(self, type, value=None, term=None):
        token = self.skip(type, value)
        if token is not None:
            return token
        if term is None:
            term = repr(value is None and type or value)
        if not self.tokens:
            raise RuleError('expected %s but end of rule reached' % term)
        raise RuleError('expected %s but got %r' % (term, self.tokens[-1][1]))

    def condition(self):
        op = self.and_condition()
        while self.skip('word', 'or'):
            op = 'or', (op, self.and_condition())
        return op

    def and_condition(self):
        op = self.relation()
        while self.skip('word', 'and'):
            op = 'and', (op, self.relation())
        return op

    def relation(self):
        left = self.expr()
        if self.skip('word', 'is'):
            return self.skip('word', 'not') and 'isnot' or 'is', \
                   (left, self.value())
        negated = self.skip('word', 'not')
        method = 'in'
        if self.skip('word', 'within'):
            method = 'within'
        else:
            self.expect('word', 'in', term="'within' or 'in'")
        rv = 'relation', (method, left, self.range_list())
        if negated:
            rv = 'not', (rv,)
        return rv

    def range_or_value(self):
        left = self.value()
        if self.skip('ellipsis'):
            return((left, self.value()))
        else:
            return((left, left))

    def range_list(self):
        range_list = [self.range_or_value()]
        while self.skip('comma'):
            range_list.append(self.range_or_value())
        return 'range_list', range_list

    def expr(self):
        self.expect('word', 'n')
        if self.skip('word', 'mod'):
            return 'mod', (('n', ()), self.value())
        return 'n', ()

    def value(self):
        return 'value', (int(self.expect('value')[1]),)


def _binary_compiler(tmpl):
    """Compiler factory for the `_Compiler`."""
    return lambda self, l, r: tmpl % (self.compile(l), self.compile(r))


def _unary_compiler(tmpl):
    """Compiler factory for the `_Compiler`."""
    return lambda self, x: tmpl % self.compile(x)


class _Compiler(object):
    """The compilers are able to transform the expressions into multiple
    output formats.
    """

    def compile(self, arg):
        op, args = arg
        return getattr(self, 'compile_' + op)(*args)

    compile_n = lambda x: 'n'
    compile_value = lambda x, v: str(v)
    compile_and = _binary_compiler('(%s && %s)')
    compile_or = _binary_compiler('(%s || %s)')
    compile_not = _unary_compiler('(!%s)')
    compile_mod = _binary_compiler('(%s %% %s)')
    compile_is = _binary_compiler('(%s == %s)')
    compile_isnot = _binary_compiler('(%s != %s)')

    def compile_relation(self, method, expr, range_list):
        raise NotImplementedError()


class _PythonCompiler(_Compiler):
    """Compiles an expression to Python."""

    compile_and = _binary_compiler('(%s and %s)')
    compile_or = _binary_compiler('(%s or %s)')
    compile_not = _unary_compiler('(not %s)')
    compile_mod = _binary_compiler('MOD(%s, %s)')

    def compile_relation(self, method, expr, range_list):
        compile_range_list = '[%s]' % ','.join(
            ['(%s, %s)' % tuple(map(self.compile, range_))
             for range_ in range_list[1]])
        return '%s(%s, %s)' % (method.upper(), self.compile(expr),
                               compile_range_list)


class _GettextCompiler(_Compiler):
    """Compile into a gettext plural expression."""

    def compile_relation(self, method, expr, range_list):
        rv = []
        expr = self.compile(expr)
        for item in range_list[1]:
            if item[0] == item[1]:
                rv.append('(%s == %s)' % (
                    expr,
                    self.compile(item[0])
                ))
            else:
                min, max = map(self.compile, item)
                rv.append('(%s >= %s && %s <= %s)' % (
                    expr,
                    min,
                    expr,
                    max
                ))
        return '(%s)' % ' || '.join(rv)


class _JavaScriptCompiler(_GettextCompiler):
    """Compiles the expression to plain of JavaScript."""

    def compile_relation(self, method, expr, range_list):
        code = _GettextCompiler.compile_relation(
            self, method, expr, range_list)
        if method == 'in':
            expr = self.compile(expr)
            code = '(parseInt(%s) == %s && %s)' % (expr, expr, code)
        return code


class _UnicodeCompiler(_Compiler):
    """Returns a unicode pluralization rule again."""

    compile_is = _binary_compiler('%s is %s')
    compile_isnot = _binary_compiler('%s is not %s')
    compile_and = _binary_compiler('%s and %s')
    compile_or = _binary_compiler('%s or %s')
    compile_mod = _binary_compiler('%s mod %s')

    def compile_not(self, relation):
        return self.compile_relation(negated=True, *relation[1])

    def compile_relation(self, method, expr, range_list, negated=False):
        ranges = []
        for item in range_list[1]:
            if item[0] == item[1]:
                ranges.append(self.compile(item[0]))
            else:
                ranges.append('%s..%s' % tuple(map(self.compile, item)))
        return '%s%s %s %s' % (
            self.compile(expr), negated and ' not' or '',
            method, ','.join(ranges)
        )

########NEW FILE########
__FILENAME__ = support
# -*- coding: utf-8 -*-
"""
    babel.support
    ~~~~~~~~~~~~~

    Several classes and functions that help with integrating and using Babel
    in applications.

    .. note: the code in this module is not used by Babel itself

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import gettext
import locale

from babel.core import Locale
from babel.dates import format_date, format_datetime, format_time, \
     format_timedelta
from babel.numbers import format_number, format_decimal, format_currency, \
     format_percent, format_scientific
from babel._compat import PY2, text_type, text_to_native


class Format(object):
    """Wrapper class providing the various date and number formatting functions
    bound to a specific locale and time-zone.

    >>> from babel.util import UTC
    >>> from datetime import date
    >>> fmt = Format('en_US', UTC)
    >>> fmt.date(date(2007, 4, 1))
    u'Apr 1, 2007'
    >>> fmt.decimal(1.2345)
    u'1.234'
    """

    def __init__(self, locale, tzinfo=None):
        """Initialize the formatter.

        :param locale: the locale identifier or `Locale` instance
        :param tzinfo: the time-zone info (a `tzinfo` instance or `None`)
        """
        self.locale = Locale.parse(locale)
        self.tzinfo = tzinfo

    def date(self, date=None, format='medium'):
        """Return a date formatted according to the given pattern.

        >>> from datetime import date
        >>> fmt = Format('en_US')
        >>> fmt.date(date(2007, 4, 1))
        u'Apr 1, 2007'
        """
        return format_date(date, format, locale=self.locale)

    def datetime(self, datetime=None, format='medium'):
        """Return a date and time formatted according to the given pattern.

        >>> from datetime import datetime
        >>> from pytz import timezone
        >>> fmt = Format('en_US', tzinfo=timezone('US/Eastern'))
        >>> fmt.datetime(datetime(2007, 4, 1, 15, 30))
        u'Apr 1, 2007, 11:30:00 AM'
        """
        return format_datetime(datetime, format, tzinfo=self.tzinfo,
                               locale=self.locale)

    def time(self, time=None, format='medium'):
        """Return a time formatted according to the given pattern.

        >>> from datetime import datetime
        >>> from pytz import timezone
        >>> fmt = Format('en_US', tzinfo=timezone('US/Eastern'))
        >>> fmt.time(datetime(2007, 4, 1, 15, 30))
        u'11:30:00 AM'
        """
        return format_time(time, format, tzinfo=self.tzinfo, locale=self.locale)

    def timedelta(self, delta, granularity='second', threshold=.85,
                  format='medium', add_direction=False):
        """Return a time delta according to the rules of the given locale.

        >>> from datetime import timedelta
        >>> fmt = Format('en_US')
        >>> fmt.timedelta(timedelta(weeks=11))
        u'3 months'
        """
        return format_timedelta(delta, granularity=granularity,
                                threshold=threshold,
                                format=format, add_direction=add_direction,
                                locale=self.locale)

    def number(self, number):
        """Return an integer number formatted for the locale.

        >>> fmt = Format('en_US')
        >>> fmt.number(1099)
        u'1,099'
        """
        return format_number(number, locale=self.locale)

    def decimal(self, number, format=None):
        """Return a decimal number formatted for the locale.

        >>> fmt = Format('en_US')
        >>> fmt.decimal(1.2345)
        u'1.234'
        """
        return format_decimal(number, format, locale=self.locale)

    def currency(self, number, currency):
        """Return a number in the given currency formatted for the locale.
        """
        return format_currency(number, currency, locale=self.locale)

    def percent(self, number, format=None):
        """Return a number formatted as percentage for the locale.

        >>> fmt = Format('en_US')
        >>> fmt.percent(0.34)
        u'34%'
        """
        return format_percent(number, format, locale=self.locale)

    def scientific(self, number):
        """Return a number formatted using scientific notation for the locale.
        """
        return format_scientific(number, locale=self.locale)


class LazyProxy(object):
    """Class for proxy objects that delegate to a specified function to evaluate
    the actual object.

    >>> def greeting(name='world'):
    ...     return 'Hello, %s!' % name
    >>> lazy_greeting = LazyProxy(greeting, name='Joe')
    >>> print lazy_greeting
    Hello, Joe!
    >>> u'  ' + lazy_greeting
    u'  Hello, Joe!'
    >>> u'(%s)' % lazy_greeting
    u'(Hello, Joe!)'

    This can be used, for example, to implement lazy translation functions that
    delay the actual translation until the string is actually used. The
    rationale for such behavior is that the locale of the user may not always
    be available. In web applications, you only know the locale when processing
    a request.

    The proxy implementation attempts to be as complete as possible, so that
    the lazy objects should mostly work as expected, for example for sorting:

    >>> greetings = [
    ...     LazyProxy(greeting, 'world'),
    ...     LazyProxy(greeting, 'Joe'),
    ...     LazyProxy(greeting, 'universe'),
    ... ]
    >>> greetings.sort()
    >>> for greeting in greetings:
    ...     print greeting
    Hello, Joe!
    Hello, universe!
    Hello, world!
    """
    __slots__ = ['_func', '_args', '_kwargs', '_value', '_is_cache_enabled']

    def __init__(self, func, *args, **kwargs):
        is_cache_enabled = kwargs.pop('enable_cache', True)
        # Avoid triggering our own __setattr__ implementation
        object.__setattr__(self, '_func', func)
        object.__setattr__(self, '_args', args)
        object.__setattr__(self, '_kwargs', kwargs)
        object.__setattr__(self, '_is_cache_enabled', is_cache_enabled)
        object.__setattr__(self, '_value', None)

    @property
    def value(self):
        if self._value is None:
            value = self._func(*self._args, **self._kwargs)
            if not self._is_cache_enabled:
                return value
            object.__setattr__(self, '_value', value)
        return self._value

    def __contains__(self, key):
        return key in self.value

    def __nonzero__(self):
        return bool(self.value)

    def __dir__(self):
        return dir(self.value)

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return unicode(self.value)

    def __add__(self, other):
        return self.value + other

    def __radd__(self, other):
        return other + self.value

    def __mod__(self, other):
        return self.value % other

    def __rmod__(self, other):
        return other % self.value

    def __mul__(self, other):
        return self.value * other

    def __rmul__(self, other):
        return other * self.value

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)

    def __lt__(self, other):
        return self.value < other

    def __le__(self, other):
        return self.value <= other

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other

    def __gt__(self, other):
        return self.value > other

    def __ge__(self, other):
        return self.value >= other

    def __delattr__(self, name):
        delattr(self.value, name)

    def __getattr__(self, name):
        return getattr(self.value, name)

    def __setattr__(self, name, value):
        setattr(self.value, name, value)

    def __delitem__(self, key):
        del self.value[key]

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        self.value[key] = value


class NullTranslations(gettext.NullTranslations, object):

    DEFAULT_DOMAIN = None

    def __init__(self, fp=None):
        """Initialize a simple translations class which is not backed by a
        real catalog. Behaves similar to gettext.NullTranslations but also
        offers Babel's on *gettext methods (e.g. 'dgettext()').

        :param fp: a file-like object (ignored in this class)
        """
        # These attributes are set by gettext.NullTranslations when a catalog
        # is parsed (fp != None). Ensure that they are always present because
        # some *gettext methods (including '.gettext()') rely on the attributes.
        self._catalog = {}
        self.plural = lambda n: int(n != 1)
        super(NullTranslations, self).__init__(fp=fp)
        self.files = filter(None, [getattr(fp, 'name', None)])
        self.domain = self.DEFAULT_DOMAIN
        self._domains = {}

    def dgettext(self, domain, message):
        """Like ``gettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).gettext(message)

    def ldgettext(self, domain, message):
        """Like ``lgettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).lgettext(message)

    def udgettext(self, domain, message):
        """Like ``ugettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ugettext(message)
    # backward compatibility with 0.9
    dugettext = udgettext

    def dngettext(self, domain, singular, plural, num):
        """Like ``ngettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ngettext(singular, plural, num)

    def ldngettext(self, domain, singular, plural, num):
        """Like ``lngettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).lngettext(singular, plural, num)

    def udngettext(self, domain, singular, plural, num):
        """Like ``ungettext()`` but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ungettext(singular, plural, num)
    # backward compatibility with 0.9
    dungettext  = udngettext

    # Most of the downwards code, until it get's included in stdlib, from:
    #    http://bugs.python.org/file10036/gettext-pgettext.patch
    #
    # The encoding of a msgctxt and a msgid in a .mo file is
    # msgctxt + "\x04" + msgid (gettext version >= 0.15)
    CONTEXT_ENCODING = '%s\x04%s'

    def pgettext(self, context, message):
        """Look up the `context` and `message` id in the catalog and return the
        corresponding message string, as an 8-bit string encoded with the
        catalog's charset encoding, if known.  If there is no entry in the
        catalog for the `message` id and `context` , and a fallback has been
        set, the look up is forwarded to the fallback's ``pgettext()``
        method. Otherwise, the `message` id is returned.
        """
        ctxt_msg_id = self.CONTEXT_ENCODING % (context, message)
        missing = object()
        tmsg = self._catalog.get(ctxt_msg_id, missing)
        if tmsg is missing:
            if self._fallback:
                return self._fallback.pgettext(context, message)
            return message
        # Encode the Unicode tmsg back to an 8-bit string, if possible
        if self._output_charset:
            return text_to_native(tmsg, self._output_charset)
        elif self._charset:
            return text_to_native(tmsg, self._charset)
        return tmsg

    def lpgettext(self, context, message):
        """Equivalent to ``pgettext()``, but the translation is returned in the
        preferred system encoding, if no other encoding was explicitly set with
        ``bind_textdomain_codeset()``.
        """
        ctxt_msg_id = self.CONTEXT_ENCODING % (context, message)
        missing = object()
        tmsg = self._catalog.get(ctxt_msg_id, missing)
        if tmsg is missing:
            if self._fallback:
                return self._fallback.lpgettext(context, message)
            return message
        if self._output_charset:
            return tmsg.encode(self._output_charset)
        return tmsg.encode(locale.getpreferredencoding())

    def npgettext(self, context, singular, plural, num):
        """Do a plural-forms lookup of a message id.  `singular` is used as the
        message id for purposes of lookup in the catalog, while `num` is used to
        determine which plural form to use.  The returned message string is an
        8-bit string encoded with the catalog's charset encoding, if known.

        If the message id for `context` is not found in the catalog, and a
        fallback is specified, the request is forwarded to the fallback's
        ``npgettext()`` method.  Otherwise, when ``num`` is 1 ``singular`` is
        returned, and ``plural`` is returned in all other cases.
        """
        ctxt_msg_id = self.CONTEXT_ENCODING % (context, singular)
        try:
            tmsg = self._catalog[(ctxt_msg_id, self.plural(num))]
            if self._output_charset:
                return text_to_native(tmsg, self._output_charset)
            elif self._charset:
                return text_to_native(tmsg, self._charset)
            return tmsg
        except KeyError:
            if self._fallback:
                return self._fallback.npgettext(context, singular, plural, num)
            if num == 1:
                return singular
            else:
                return plural

    def lnpgettext(self, context, singular, plural, num):
        """Equivalent to ``npgettext()``, but the translation is returned in the
        preferred system encoding, if no other encoding was explicitly set with
        ``bind_textdomain_codeset()``.
        """
        ctxt_msg_id = self.CONTEXT_ENCODING % (context, singular)
        try:
            tmsg = self._catalog[(ctxt_msg_id, self.plural(num))]
            if self._output_charset:
                return tmsg.encode(self._output_charset)
            return tmsg.encode(locale.getpreferredencoding())
        except KeyError:
            if self._fallback:
                return self._fallback.lnpgettext(context, singular, plural, num)
            if num == 1:
                return singular
            else:
                return plural

    def upgettext(self, context, message):
        """Look up the `context` and `message` id in the catalog and return the
        corresponding message string, as a Unicode string.  If there is no entry
        in the catalog for the `message` id and `context`, and a fallback has
        been set, the look up is forwarded to the fallback's ``upgettext()``
        method.  Otherwise, the `message` id is returned.
        """
        ctxt_message_id = self.CONTEXT_ENCODING % (context, message)
        missing = object()
        tmsg = self._catalog.get(ctxt_message_id, missing)
        if tmsg is missing:
            if self._fallback:
                return self._fallback.upgettext(context, message)
            return text_type(message)
        return tmsg

    def unpgettext(self, context, singular, plural, num):
        """Do a plural-forms lookup of a message id.  `singular` is used as the
        message id for purposes of lookup in the catalog, while `num` is used to
        determine which plural form to use.  The returned message string is a
        Unicode string.

        If the message id for `context` is not found in the catalog, and a
        fallback is specified, the request is forwarded to the fallback's
        ``unpgettext()`` method.  Otherwise, when `num` is 1 `singular` is
        returned, and `plural` is returned in all other cases.
        """
        ctxt_message_id = self.CONTEXT_ENCODING % (context, singular)
        try:
            tmsg = self._catalog[(ctxt_message_id, self.plural(num))]
        except KeyError:
            if self._fallback:
                return self._fallback.unpgettext(context, singular, plural, num)
            if num == 1:
                tmsg = text_type(singular)
            else:
                tmsg = text_type(plural)
        return tmsg

    def dpgettext(self, domain, context, message):
        """Like `pgettext()`, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).pgettext(context, message)

    def udpgettext(self, domain, context, message):
        """Like `upgettext()`, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).upgettext(context, message)
    # backward compatibility with 0.9
    dupgettext = udpgettext

    def ldpgettext(self, domain, context, message):
        """Equivalent to ``dpgettext()``, but the translation is returned in the
        preferred system encoding, if no other encoding was explicitly set with
        ``bind_textdomain_codeset()``.
        """
        return self._domains.get(domain, self).lpgettext(context, message)

    def dnpgettext(self, domain, context, singular, plural, num):
        """Like ``npgettext``, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).npgettext(context, singular,
                                                         plural, num)

    def udnpgettext(self, domain, context, singular, plural, num):
        """Like ``unpgettext``, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).unpgettext(context, singular,
                                                          plural, num)
    # backward compatibility with 0.9
    dunpgettext = udnpgettext

    def ldnpgettext(self, domain, context, singular, plural, num):
        """Equivalent to ``dnpgettext()``, but the translation is returned in
        the preferred system encoding, if no other encoding was explicitly set
        with ``bind_textdomain_codeset()``.
        """
        return self._domains.get(domain, self).lnpgettext(context, singular,
                                                          plural, num)

    if not PY2:
        ugettext = gettext.NullTranslations.gettext
        ungettext = gettext.NullTranslations.ngettext


class Translations(NullTranslations, gettext.GNUTranslations):
    """An extended translation catalog class."""

    DEFAULT_DOMAIN = 'messages'

    def __init__(self, fp=None, domain=None):
        """Initialize the translations catalog.

        :param fp: the file-like object the translation should be read from
        :param domain: the message domain (default: 'messages')
        """
        super(Translations, self).__init__(fp=fp)
        self.domain = domain or self.DEFAULT_DOMAIN

    if not PY2:
        ugettext = gettext.GNUTranslations.gettext
        ungettext = gettext.GNUTranslations.ngettext

    @classmethod
    def load(cls, dirname=None, locales=None, domain=None):
        """Load translations from the given directory.

        :param dirname: the directory containing the ``MO`` files
        :param locales: the list of locales in order of preference (items in
                        this list can be either `Locale` objects or locale
                        strings)
        :param domain: the message domain (default: 'messages')
        """
        if locales is not None:
            if not isinstance(locales, (list, tuple)):
                locales = [locales]
            locales = [str(locale) for locale in locales]
        if not domain:
            domain = cls.DEFAULT_DOMAIN
        filename = gettext.find(domain, dirname, locales)
        if not filename:
            return NullTranslations()
        with open(filename, 'rb') as fp:
            return cls(fp=fp, domain=domain)

    def __repr__(self):
        return '<%s: "%s">' % (type(self).__name__,
                               self._info.get('project-id-version'))

    def add(self, translations, merge=True):
        """Add the given translations to the catalog.

        If the domain of the translations is different than that of the
        current catalog, they are added as a catalog that is only accessible
        by the various ``d*gettext`` functions.

        :param translations: the `Translations` instance with the messages to
                             add
        :param merge: whether translations for message domains that have
                      already been added should be merged with the existing
                      translations
        """
        domain = getattr(translations, 'domain', self.DEFAULT_DOMAIN)
        if merge and domain == self.domain:
            return self.merge(translations)

        existing = self._domains.get(domain)
        if merge and existing is not None:
            existing.merge(translations)
        else:
            translations.add_fallback(self)
            self._domains[domain] = translations

        return self

    def merge(self, translations):
        """Merge the given translations into the catalog.

        Message translations in the specified catalog override any messages
        with the same identifier in the existing catalog.

        :param translations: the `Translations` instance with the messages to
                             merge
        """
        if isinstance(translations, gettext.GNUTranslations):
            self._catalog.update(translations._catalog)
            if isinstance(translations, Translations):
                self.files.extend(translations.files)

        return self

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
"""
    babel.util
    ~~~~~~~~~~

    Various utility classes and functions.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import codecs
from datetime import timedelta, tzinfo
import os
import re
import textwrap
from babel._compat import izip, imap

missing = object()


def distinct(iterable):
    """Yield all items in an iterable collection that are distinct.

    Unlike when using sets for a similar effect, the original ordering of the
    items in the collection is preserved by this function.

    >>> print list(distinct([1, 2, 1, 3, 4, 4]))
    [1, 2, 3, 4]
    >>> print list(distinct('foobar'))
    ['f', 'o', 'b', 'a', 'r']

    :param iterable: the iterable collection providing the data
    """
    seen = set()
    for item in iter(iterable):
        if item not in seen:
            yield item
            seen.add(item)

# Regexp to match python magic encoding line
PYTHON_MAGIC_COMMENT_re = re.compile(
    br'[ \t\f]* \# .* coding[=:][ \t]*([-\w.]+)', re.VERBOSE)
def parse_encoding(fp):
    """Deduce the encoding of a source file from magic comment.

    It does this in the same way as the `Python interpreter`__

    .. __: http://docs.python.org/ref/encodings.html

    The ``fp`` argument should be a seekable file object.

    (From Jeff Dairiki)
    """
    pos = fp.tell()
    fp.seek(0)
    try:
        line1 = fp.readline()
        has_bom = line1.startswith(codecs.BOM_UTF8)
        if has_bom:
            line1 = line1[len(codecs.BOM_UTF8):]

        m = PYTHON_MAGIC_COMMENT_re.match(line1)
        if not m:
            try:
                import parser
                parser.suite(line1.decode('latin-1'))
            except (ImportError, SyntaxError):
                # Either it's a real syntax error, in which case the source is
                # not valid python source, or line2 is a continuation of line1,
                # in which case we don't want to scan line2 for a magic
                # comment.
                pass
            else:
                line2 = fp.readline()
                m = PYTHON_MAGIC_COMMENT_re.match(line2)

        if has_bom:
            if m:
                raise SyntaxError(
                    "python refuses to compile code with both a UTF8 "
                    "byte-order-mark and a magic encoding comment")
            return 'utf-8'
        elif m:
            return m.group(1).decode('latin-1')
        else:
            return None
    finally:
        fp.seek(pos)

def pathmatch(pattern, filename):
    """Extended pathname pattern matching.

    This function is similar to what is provided by the ``fnmatch`` module in
    the Python standard library, but:

     * can match complete (relative or absolute) path names, and not just file
       names, and
     * also supports a convenience pattern ("**") to match files at any
       directory level.

    Examples:

    >>> pathmatch('**.py', 'bar.py')
    True
    >>> pathmatch('**.py', 'foo/bar/baz.py')
    True
    >>> pathmatch('**.py', 'templates/index.html')
    False

    >>> pathmatch('**/templates/*.html', 'templates/index.html')
    True
    >>> pathmatch('**/templates/*.html', 'templates/foo/bar.html')
    False

    :param pattern: the glob pattern
    :param filename: the path name of the file to match against
    """
    symbols = {
        '?':   '[^/]',
        '?/':  '[^/]/',
        '*':   '[^/]+',
        '*/':  '[^/]+/',
        '**/': '(?:.+/)*?',
        '**':  '(?:.+/)*?[^/]+',
    }
    buf = []
    for idx, part in enumerate(re.split('([?*]+/?)', pattern)):
        if idx % 2:
            buf.append(symbols[part])
        elif part:
            buf.append(re.escape(part))
    match = re.match(''.join(buf) + '$', filename.replace(os.sep, '/'))
    return match is not None


class TextWrapper(textwrap.TextWrapper):
    wordsep_re = re.compile(
        r'(\s+|'                                  # any whitespace
        r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w))'    # em-dash
    )


def wraptext(text, width=70, initial_indent='', subsequent_indent=''):
    """Simple wrapper around the ``textwrap.wrap`` function in the standard
    library. This version does not wrap lines on hyphens in words.

    :param text: the text to wrap
    :param width: the maximum line width
    :param initial_indent: string that will be prepended to the first line of
                           wrapped output
    :param subsequent_indent: string that will be prepended to all lines save
                              the first of wrapped output
    """
    wrapper = TextWrapper(width=width, initial_indent=initial_indent,
                          subsequent_indent=subsequent_indent,
                          break_long_words=False)
    return wrapper.wrap(text)


class odict(dict):
    """Ordered dict implementation.

    :see: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/107747
    """
    def __init__(self, data=None):
        dict.__init__(self, data or {})
        self._keys = list(dict.keys(self))

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        dict.__setitem__(self, key, item)
        if key not in self._keys:
            self._keys.append(key)

    def __iter__(self):
        return iter(self._keys)
    iterkeys = __iter__

    def clear(self):
        dict.clear(self)
        self._keys = []

    def copy(self):
        d = odict()
        d.update(self)
        return d

    def items(self):
        return zip(self._keys, self.values())

    def iteritems(self):
        return izip(self._keys, self.itervalues())

    def keys(self):
        return self._keys[:]

    def pop(self, key, default=missing):
        if default is missing:
            return dict.pop(self, key)
        elif key not in self:
            return default
        self._keys.remove(key)
        return dict.pop(self, key, default)

    def popitem(self, key):
        self._keys.remove(key)
        return dict.popitem(key)

    def setdefault(self, key, failobj = None):
        dict.setdefault(self, key, failobj)
        if key not in self._keys:
            self._keys.append(key)

    def update(self, dict):
        for (key, val) in dict.items():
            self[key] = val

    def values(self):
        return map(self.get, self._keys)

    def itervalues(self):
        return imap(self.get, self._keys)


try:
    relpath = os.path.relpath
except AttributeError:
    def relpath(path, start='.'):
        """Compute the relative path to one path from another.

        >>> relpath('foo/bar.txt', '').replace(os.sep, '/')
        'foo/bar.txt'
        >>> relpath('foo/bar.txt', 'foo').replace(os.sep, '/')
        'bar.txt'
        >>> relpath('foo/bar.txt', 'baz').replace(os.sep, '/')
        '../foo/bar.txt'
        """
        start_list = os.path.abspath(start).split(os.sep)
        path_list = os.path.abspath(path).split(os.sep)

        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list) - i) + path_list[i:]
        return os.path.join(*rel_list)


class FixedOffsetTimezone(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name=None):
        self._offset = timedelta(minutes=offset)
        if name is None:
            name = 'Etc/GMT+%d' % offset
        self.zone = name

    def __str__(self):
        return self.zone

    def __repr__(self):
        return '<FixedOffset "%s" %s>' % (self.zone, self._offset)

    def utcoffset(self, dt):
        return self._offset

    def tzname(self, dt):
        return self.zone

    def dst(self, dt):
        return ZERO


import pytz as _pytz
from babel import localtime

# Export the localtime functionality here because that's
# where it was in the past.
UTC = _pytz.utc
LOCALTZ = localtime.LOCALTZ
get_localzone = localtime.get_localzone

STDOFFSET = localtime.STDOFFSET
DSTOFFSET = localtime.DSTOFFSET
DSTDIFF = localtime.DSTDIFF
ZERO = localtime.ZERO

########NEW FILE########
__FILENAME__ = _compat
import sys
import array

PY2 = sys.version_info[0] == 2

_identity = lambda x: x


if not PY2:
    text_type = str
    string_types = (str,)
    integer_types = (int, )
    unichr = chr

    text_to_native = lambda s, enc: s

    iterkeys = lambda d: iter(d.keys())
    itervalues = lambda d: iter(d.values())
    iteritems = lambda d: iter(d.items())

    from io import StringIO, BytesIO
    import pickle

    izip = zip
    imap = map
    range_type = range

    cmp = lambda a, b: (a > b) - (a < b)

    array_tobytes = array.array.tobytes

else:
    text_type = unicode
    string_types = (str, unicode)
    integer_types = (int, long)

    text_to_native = lambda s, enc: s.encode(enc)
    unichr = unichr

    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()

    from cStringIO import StringIO as BytesIO
    from StringIO import StringIO
    import cPickle as pickle

    from itertools import izip, imap
    range_type = xrange

    cmp = cmp

    array_tobytes = array.array.tostring


number_types = integer_types + (float,)

########NEW FILE########
__FILENAME__ = conftest
import sys
from _pytest.doctest import DoctestModule
from py.path import local


PY2 = sys.version_info[0] < 3


collect_ignore = ['tests/messages/data']


def pytest_collect_file(path, parent):
    babel_path = local(__file__).dirpath().join('babel')
    config = parent.config
    if PY2:
        if babel_path.common(path) == babel_path:
            if path.ext == ".py":
                return DoctestModule(path, parent)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Babel documentation build configuration file, created by
# sphinx-quickstart on Wed Jul  3 17:53:01 2013.
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
sys.path.append(os.path.abspath('_themes'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.intersphinx',
              'sphinx.ext.extlinks']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Babel'
copyright = u'2013, The Babel Team'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

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
exclude_patterns = ['_build']

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
html_theme = 'babel'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

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
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    'index':    ['sidebar-about.html', 'localtoc.html', 'sidebar-links.html',
                 'searchbox.html'],
    '**':       ['sidebar-logo.html', 'localtoc.html', 'relations.html',
                 'searchbox.html']
}

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
html_show_sourcelink = False

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
htmlhelp_basename = 'Babeldoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',

# Needed for unicode symbol conversion.
'fontpkg': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Babel.tex', u'Babel Documentation',
   u'The Babel Team', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
latex_logo = '_static/logo.png'

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
    ('index_', 'babel', u'Babel Documentation',
     [u'The Babel Team'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index_', 'Babel', u'Babel Documentation',
   u'The Babel Team', 'Babel', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

intersphinx_mapping = {
    'http://docs.python.org/2': None,
}

extlinks = {
    'gh': ('https://github.com/mitsuhiko/babel/issues/%s', '#'),
    'trac': ('http://babel.edgewall.org/ticket/%s', 'ticket #'),
}

########NEW FILE########
__FILENAME__ = download_import_cldr
#!/usr/bin/env python

import os
import sys
import shutil
import hashlib
import zipfile
import urllib
import subprocess
try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve


URL = 'http://unicode.org/Public/cldr/23.1/core.zip'
FILENAME = 'core-23.1.zip'
FILESUM = 'd44ff35f9b9160becbb3a575468d8a5a'
BLKSIZE = 131072


def get_terminal_width():
    try:
        import fcntl
        import termios
        import struct
        fd = sys.stdin.fileno()
        cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        return cr[1]
    except Exception:
        return 80


def reporthook(block_count, block_size, total_size):
    bytes_transmitted = block_count * block_size
    cols = get_terminal_width()
    buffer = 6
    percent = float(bytes_transmitted) / (total_size or 1)
    done = int(percent * (cols - buffer))
    sys.stdout.write('\r')
    sys.stdout.write(' ' + '=' * done + ' ' * (cols - done - buffer))
    sys.stdout.write('% 4d%%' % (percent * 100))
    sys.stdout.flush()


def log(message, *args):
    if args:
        message = message % args
    sys.stderr.write(message + '\n')


def is_good_file(filename):
    if not os.path.isfile(filename):
        log('Local copy \'%s\' not found', filename)
        return False
    h = hashlib.md5()
    with open(filename, 'rb') as f:
        while 1:
            blk = f.read(BLKSIZE)
            if not blk:
                break
            h.update(blk)
        digest = h.hexdigest()
        if digest != FILESUM:
            raise RuntimeError('Checksum mismatch: %r != %r'
                               % (digest, FILESUM))
        else:
            return True


def main():
    scripts_path = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(scripts_path)
    cldr_path = os.path.join(repo, 'cldr')
    zip_path = os.path.join(cldr_path, FILENAME)
    changed = False

    while not is_good_file(zip_path):
        log('Downloading \'%s\'', FILENAME)
        if os.path.isfile(zip_path):
            os.remove(zip_path)
        urlretrieve(URL, zip_path, reporthook)
        changed = True
        print
    common_path = os.path.join(cldr_path, 'common')

    if changed or not os.path.isdir(common_path):
        if os.path.isdir(common_path):
            log('Deleting old CLDR checkout in \'%s\'', cldr_path)
            shutil.rmtree(common_path)

        log('Extracting CLDR to \'%s\'', cldr_path)
        z = zipfile.ZipFile(zip_path)
        z.extractall(cldr_path)
        z.close()

    subprocess.check_call([
        sys.executable,
        os.path.join(scripts_path, 'import_cldr.py'),
        common_path])


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = dump_data
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

from optparse import OptionParser
from pprint import pprint

from babel.localedata import load, LocaleDataDict


def main():
    parser = OptionParser(usage='%prog [options] locale [path]')
    parser.add_option('--noinherit', action='store_false', dest='inherit',
                      help='do not merge inherited data into locale data')
    parser.add_option('--resolve', action='store_true', dest='resolve',
                      help='resolve aliases in locale data')
    parser.set_defaults(inherit=True, resolve=False)
    options, args = parser.parse_args()
    if len(args) not in (1, 2):
        parser.error('incorrect number of arguments')

    data = load(args[0], merge_inherited=options.inherit)
    if options.resolve:
        data = LocaleDataDict(data)
    if len(args) > 1:
        for key in args[1].split('.'):
            data = data[key]
    if isinstance(data, dict):
        data = dict(data.items())
    pprint(data)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = dump_global
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import cPickle as pickle
import os
from pprint import pprint
import sys

import babel

dirname = os.path.join(os.path.dirname(babel.__file__))
filename = os.path.join(dirname, 'global.dat')
fileobj = open(filename, 'rb')
try:
    data = pickle.load(fileobj)
finally:
    fileobj.close()

if len(sys.argv) > 1:
    pprint(data.get(sys.argv[1]))
else:
    pprint(data)

########NEW FILE########
__FILENAME__ = import_cldr
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

from optparse import OptionParser
import os
import re
import sys
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree

from datetime import date

# Make sure we're using Babel source, and not some previously installed version
sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]), '..'))

from babel import dates, numbers
from babel.plural import PluralRule
from babel.localedata import Alias
from babel._compat import pickle, text_type

parse = ElementTree.parse
weekdays = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5,
            'sun': 6}


def _text(elem):
    buf = [elem.text or '']
    for child in elem:
        buf.append(_text(child))
    buf.append(elem.tail or '')
    return u''.join(filter(None, buf)).strip()


NAME_RE = re.compile(r"^\w+$")
TYPE_ATTR_RE = re.compile(r"^\w+\[@type='(.*?)'\]$")

NAME_MAP = {
    'dateFormats': 'date_formats',
    'dateTimeFormats': 'datetime_formats',
    'eraAbbr': 'abbreviated',
    'eraNames': 'wide',
    'eraNarrow': 'narrow',
    'timeFormats': 'time_formats'
}


def log(message, *args):
    if args:
        message = message % args
    sys.stderr.write(message + '\r\n')
    sys.stderr.flush()


def error(message, *args):
    log('ERROR: %s' % message, *args)


def need_conversion(dst_filename, data_dict, source_filename):
    with open(source_filename, 'rb') as f:
        blob = f.read(4096)
        version = int(re.search(b'version number="\\$Revision: (\\d+)',
                                blob).group(1))

    data_dict['_version'] = version
    if not os.path.isfile(dst_filename):
        return True

    with open(dst_filename, 'rb') as f:
        data = pickle.load(f)
        return data.get('_version') != version


def _translate_alias(ctxt, path):
    parts = path.split('/')
    keys = ctxt[:]
    for part in parts:
        if part == '..':
            keys.pop()
        else:
            match = TYPE_ATTR_RE.match(part)
            if match:
                keys.append(match.group(1))
            else:
                assert NAME_RE.match(part)
                keys.append(NAME_MAP.get(part, part))
    return keys


def _parse_currency_date(s):
    if not s:
        return None
    parts = s.split('-', 2)
    return date(*map(int, parts + [1] * (3 - len(parts))))


def _currency_sort_key(tup):
    code, start, end, tender = tup
    return int(not tender), start or date(1, 1, 1)


def main():
    parser = OptionParser(usage='%prog path/to/cldr')
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error('incorrect number of arguments')

    srcdir = args[0]
    destdir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                           '..', 'babel')

    sup_filename = os.path.join(srcdir, 'supplemental', 'supplementalData.xml')
    bcp47_timezone = parse(os.path.join(srcdir, 'bcp47', 'timezone.xml'))
    sup_windows_zones = parse(os.path.join(srcdir, 'supplemental',
                                           'windowsZones.xml'))
    sup_metadata = parse(os.path.join(srcdir, 'supplemental',
                                      'supplementalMetadata.xml'))
    sup_likely = parse(os.path.join(srcdir, 'supplemental',
                                    'likelySubtags.xml'))
    sup = parse(sup_filename)

    # Import global data from the supplemental files
    global_path = os.path.join(destdir, 'global.dat')
    global_data = {}
    if need_conversion(global_path, global_data, sup_filename):
        territory_zones = global_data.setdefault('territory_zones', {})
        zone_aliases = global_data.setdefault('zone_aliases', {})
        zone_territories = global_data.setdefault('zone_territories', {})
        win_mapping = global_data.setdefault('windows_zone_mapping', {})
        language_aliases = global_data.setdefault('language_aliases', {})
        territory_aliases = global_data.setdefault('territory_aliases', {})
        script_aliases = global_data.setdefault('script_aliases', {})
        variant_aliases = global_data.setdefault('variant_aliases', {})
        likely_subtags = global_data.setdefault('likely_subtags', {})
        territory_currencies = global_data.setdefault('territory_currencies', {})

        # create auxiliary zone->territory map from the windows zones (we don't set
        # the 'zones_territories' map directly here, because there are some zones
        # aliases listed and we defer the decision of which ones to choose to the
        # 'bcp47' data
        _zone_territory_map = {}
        for map_zone in sup_windows_zones.findall(
                './/windowsZones/mapTimezones/mapZone'):
            if map_zone.attrib.get('territory') == '001':
                win_mapping[map_zone.attrib['other']] = \
                    map_zone.attrib['type'].split()[0]
            for tzid in text_type(map_zone.attrib['type']).split():
                _zone_territory_map[tzid] = \
                    text_type(map_zone.attrib['territory'])

        for key_elem in bcp47_timezone.findall('.//keyword/key'):
            if key_elem.attrib['name'] == 'tz':
                for elem in key_elem.findall('type'):
                    aliases = text_type(elem.attrib['alias']).split()
                    tzid = aliases.pop(0)
                    territory = _zone_territory_map.get(tzid, '001')
                    territory_zones.setdefault(territory, []).append(tzid)
                    zone_territories[tzid] = territory
                    for alias in aliases:
                        zone_aliases[alias] = tzid
                break

        # Import Metazone mapping
        meta_zones = global_data.setdefault('meta_zones', {})
        tzsup = parse(os.path.join(srcdir, 'supplemental', 'metaZones.xml'))
        for elem in tzsup.findall('.//timezone'):
            for child in elem.findall('usesMetazone'):
                if 'to' not in child.attrib: # FIXME: support old mappings
                    meta_zones[elem.attrib['type']] = child.attrib['mzone']

        # Language aliases
        for alias in sup_metadata.findall('.//alias/languageAlias'):
            # We don't have a use for those at the moment.  They don't
            # pass our parser anyways.
            if '-' in alias.attrib['type']:
                continue
            language_aliases[alias.attrib['type']] = alias.attrib['replacement']

        # Territory aliases
        for alias in sup_metadata.findall('.//alias/territoryAlias'):
            territory_aliases[alias.attrib['type']] = \
                alias.attrib['replacement'].split()

        # Script aliases
        for alias in sup_metadata.findall('.//alias/scriptAlias'):
            script_aliases[alias.attrib['type']] = alias.attrib['replacement']

        # Variant aliases
        for alias in sup_metadata.findall('.//alias/variantAlias'):
            repl = alias.attrib.get('replacement')
            if repl:
                variant_aliases[alias.attrib['type']] = repl

        # Likely subtags
        for likely_subtag in sup_likely.findall('.//likelySubtags/likelySubtag'):
            likely_subtags[likely_subtag.attrib['from']] = \
                likely_subtag.attrib['to']

        # Currencies in territories
        for region in sup.findall('.//currencyData/region'):
            region_code = region.attrib['iso3166']
            region_currencies = []
            for currency in region.findall('./currency'):
                cur_start = _parse_currency_date(currency.attrib.get('from'))
                cur_end = _parse_currency_date(currency.attrib.get('to'))
                region_currencies.append((currency.attrib['iso4217'],
                                          cur_start, cur_end,
                                          currency.attrib.get(
                                              'tender', 'true') == 'true'))
            region_currencies.sort(key=_currency_sort_key)
            territory_currencies[region_code] = region_currencies

        outfile = open(global_path, 'wb')
        try:
            pickle.dump(global_data, outfile, 2)
        finally:
            outfile.close()

    # build a territory containment mapping for inheritance
    regions = {}
    for elem in sup.findall('.//territoryContainment/group'):
        regions[elem.attrib['type']] = elem.attrib['contains'].split()

    # Resolve territory containment
    territory_containment = {}
    region_items = sorted(regions.items())
    for group, territory_list in region_items:
        for territory in territory_list:
            containers = territory_containment.setdefault(territory, set([]))
            if group in territory_containment:
                containers |= territory_containment[group]
            containers.add(group)

    # prepare the per-locale plural rules definitions
    plural_rules = {}
    prsup = parse(os.path.join(srcdir, 'supplemental', 'plurals.xml'))
    for elem in prsup.findall('.//plurals/pluralRules'):
        rules = []
        for rule in elem.findall('pluralRule'):
            rules.append((rule.attrib['count'], text_type(rule.text)))
        pr = PluralRule(rules)
        for locale in elem.attrib['locales'].split():
            plural_rules[locale] = pr

    filenames = os.listdir(os.path.join(srcdir, 'main'))
    filenames.remove('root.xml')
    filenames.sort(key=len)
    filenames.insert(0, 'root.xml')

    for filename in filenames:
        stem, ext = os.path.splitext(filename)
        if ext != '.xml':
            continue

        full_filename = os.path.join(srcdir, 'main', filename)
        data_filename = os.path.join(destdir, 'localedata', stem + '.dat')

        data = {}
        if not need_conversion(data_filename, data, full_filename):
            continue

        tree = parse(full_filename)

        language = None
        elem = tree.find('.//identity/language')
        if elem is not None:
            language = elem.attrib['type']

        territory = None
        elem = tree.find('.//identity/territory')
        if elem is not None:
            territory = elem.attrib['type']
        else:
            territory = '001' # world
        regions = territory_containment.get(territory, [])

        log('Processing %s (Language = %s; Territory = %s)',
            filename, language, territory)

        # plural rules
        locale_id = '_'.join(filter(None, [
            language,
            territory != '001' and territory or None
        ]))
        if locale_id in plural_rules:
            data['plural_form'] = plural_rules[locale_id]

        # <localeDisplayNames>

        territories = data.setdefault('territories', {})
        for elem in tree.findall('.//territories/territory'):
            if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                    and elem.attrib['type'] in territories:
                continue
            territories[elem.attrib['type']] = _text(elem)

        languages = data.setdefault('languages', {})
        for elem in tree.findall('.//languages/language'):
            if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                    and elem.attrib['type'] in languages:
                continue
            languages[elem.attrib['type']] = _text(elem)

        variants = data.setdefault('variants', {})
        for elem in tree.findall('.//variants/variant'):
            if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                    and elem.attrib['type'] in variants:
                continue
            variants[elem.attrib['type']] = _text(elem)

        scripts = data.setdefault('scripts', {})
        for elem in tree.findall('.//scripts/script'):
            if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                    and elem.attrib['type'] in scripts:
                continue
            scripts[elem.attrib['type']] = _text(elem)

        # <dates>

        week_data = data.setdefault('week_data', {})
        supelem = sup.find('.//weekData')

        for elem in supelem.findall('minDays'):
            territories = elem.attrib['territories'].split()
            if territory in territories or any([r in territories for r in regions]):
                week_data['min_days'] = int(elem.attrib['count'])

        for elem in supelem.findall('firstDay'):
            territories = elem.attrib['territories'].split()
            if territory in territories or any([r in territories for r in regions]):
                week_data['first_day'] = weekdays[elem.attrib['day']]

        for elem in supelem.findall('weekendStart'):
            territories = elem.attrib['territories'].split()
            if territory in territories or any([r in territories for r in regions]):
                week_data['weekend_start'] = weekdays[elem.attrib['day']]

        for elem in supelem.findall('weekendEnd'):
            territories = elem.attrib['territories'].split()
            if territory in territories or any([r in territories for r in regions]):
                week_data['weekend_end'] = weekdays[elem.attrib['day']]

        zone_formats = data.setdefault('zone_formats', {})
        for elem in tree.findall('.//timeZoneNames/gmtFormat'):
            if 'draft' not in elem.attrib and 'alt' not in elem.attrib:
                zone_formats['gmt'] = text_type(elem.text).replace('{0}', '%s')
                break
        for elem in tree.findall('.//timeZoneNames/regionFormat'):
            if 'draft' not in elem.attrib and 'alt' not in elem.attrib:
                zone_formats['region'] = text_type(elem.text).replace('{0}', '%s')
                break
        for elem in tree.findall('.//timeZoneNames/fallbackFormat'):
            if 'draft' not in elem.attrib and 'alt' not in elem.attrib:
                zone_formats['fallback'] = text_type(elem.text) \
                    .replace('{0}', '%(0)s').replace('{1}', '%(1)s')
                break
        for elem in tree.findall('.//timeZoneNames/fallbackRegionFormat'):
            if 'draft' not in elem.attrib and 'alt' not in elem.attrib:
                zone_formats['fallback_region'] = text_type(elem.text) \
                    .replace('{0}', '%(0)s').replace('{1}', '%(1)s')
                break

        time_zones = data.setdefault('time_zones', {})
        for elem in tree.findall('.//timeZoneNames/zone'):
            info = {}
            city = elem.findtext('exemplarCity')
            if city:
                info['city'] = text_type(city)
            for child in elem.findall('long/*'):
                info.setdefault('long', {})[child.tag] = text_type(child.text)
            for child in elem.findall('short/*'):
                info.setdefault('short', {})[child.tag] = text_type(child.text)
            time_zones[elem.attrib['type']] = info

        meta_zones = data.setdefault('meta_zones', {})
        for elem in tree.findall('.//timeZoneNames/metazone'):
            info = {}
            city = elem.findtext('exemplarCity')
            if city:
                info['city'] = text_type(city)
            for child in elem.findall('long/*'):
                info.setdefault('long', {})[child.tag] = text_type(child.text)
            for child in elem.findall('short/*'):
                info.setdefault('short', {})[child.tag] = text_type(child.text)
            meta_zones[elem.attrib['type']] = info

        for calendar in tree.findall('.//calendars/calendar'):
            if calendar.attrib['type'] != 'gregorian':
                # TODO: support other calendar types
                continue

            months = data.setdefault('months', {})
            for ctxt in calendar.findall('months/monthContext'):
                ctxt_type = ctxt.attrib['type']
                ctxts = months.setdefault(ctxt_type, {})
                for width in ctxt.findall('monthWidth'):
                    width_type = width.attrib['type']
                    widths = ctxts.setdefault(width_type, {})
                    for elem in width.getiterator():
                        if elem.tag == 'month':
                            if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                                    and int(elem.attrib['type']) in widths:
                                continue
                            widths[int(elem.attrib.get('type'))] = \
                                text_type(elem.text)
                        elif elem.tag == 'alias':
                            ctxts[width_type] = Alias(
                                _translate_alias(['months', ctxt_type, width_type],
                                                 elem.attrib['path'])
                            )

            days = data.setdefault('days', {})
            for ctxt in calendar.findall('days/dayContext'):
                ctxt_type = ctxt.attrib['type']
                ctxts = days.setdefault(ctxt_type, {})
                for width in ctxt.findall('dayWidth'):
                    width_type = width.attrib['type']
                    widths = ctxts.setdefault(width_type, {})
                    for elem in width.getiterator():
                        if elem.tag == 'day':
                            dtype = weekdays[elem.attrib['type']]
                            if ('draft' in elem.attrib or
                                'alt' not in elem.attrib) \
                                    and dtype in widths:
                                continue
                            widths[dtype] = text_type(elem.text)
                        elif elem.tag == 'alias':
                            ctxts[width_type] = Alias(
                                _translate_alias(['days', ctxt_type, width_type],
                                                 elem.attrib['path'])
                            )

            quarters = data.setdefault('quarters', {})
            for ctxt in calendar.findall('quarters/quarterContext'):
                ctxt_type = ctxt.attrib['type']
                ctxts = quarters.setdefault(ctxt.attrib['type'], {})
                for width in ctxt.findall('quarterWidth'):
                    width_type = width.attrib['type']
                    widths = ctxts.setdefault(width_type, {})
                    for elem in width.getiterator():
                        if elem.tag == 'quarter':
                            if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                                    and int(elem.attrib['type']) in widths:
                                continue
                            widths[int(elem.attrib['type'])] = text_type(elem.text)
                        elif elem.tag == 'alias':
                            ctxts[width_type] = Alias(
                                _translate_alias(['quarters', ctxt_type,
                                                  width_type],
                                                 elem.attrib['path']))

            eras = data.setdefault('eras', {})
            for width in calendar.findall('eras/*'):
                width_type = NAME_MAP[width.tag]
                widths = eras.setdefault(width_type, {})
                for elem in width.getiterator():
                    if elem.tag == 'era':
                        if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                                and int(elem.attrib['type']) in widths:
                            continue
                        widths[int(elem.attrib.get('type'))] = text_type(elem.text)
                    elif elem.tag == 'alias':
                        eras[width_type] = Alias(
                            _translate_alias(['eras', width_type],
                                             elem.attrib['path'])
                        )

            # AM/PM
            periods = data.setdefault('periods', {})
            for day_period_width in calendar.findall(
                    'dayPeriods/dayPeriodContext/dayPeriodWidth'):
                if day_period_width.attrib['type'] == 'wide':
                    for day_period in day_period_width.findall('dayPeriod'):
                        if 'alt' not in day_period.attrib:
                            periods[day_period.attrib['type']] = text_type(
                                day_period.text)

            date_formats = data.setdefault('date_formats', {})
            for format in calendar.findall('dateFormats'):
                for elem in format.getiterator():
                    if elem.tag == 'dateFormatLength':
                        if 'draft' in elem.attrib and \
                                elem.attrib.get('type') in date_formats:
                            continue
                        try:
                            date_formats[elem.attrib.get('type')] = \
                                dates.parse_pattern(text_type(
                                    elem.findtext('dateFormat/pattern')))
                        except ValueError as e:
                            error(e)
                    elif elem.tag == 'alias':
                        date_formats = Alias(_translate_alias(
                            ['date_formats'], elem.attrib['path'])
                        )

            time_formats = data.setdefault('time_formats', {})
            for format in calendar.findall('timeFormats'):
                for elem in format.getiterator():
                    if elem.tag == 'timeFormatLength':
                        if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                                and elem.attrib.get('type') in time_formats:
                            continue
                        try:
                            time_formats[elem.attrib.get('type')] = \
                                dates.parse_pattern(text_type(
                                    elem.findtext('timeFormat/pattern')))
                        except ValueError as e:
                            error(e)
                    elif elem.tag == 'alias':
                        time_formats = Alias(_translate_alias(
                            ['time_formats'], elem.attrib['path'])
                        )

            datetime_formats = data.setdefault('datetime_formats', {})
            for format in calendar.findall('dateTimeFormats'):
                for elem in format.getiterator():
                    if elem.tag == 'dateTimeFormatLength':
                        if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                                and elem.attrib.get('type') in datetime_formats:
                            continue
                        try:
                            datetime_formats[elem.attrib.get('type')] = \
                                text_type(elem.findtext('dateTimeFormat/pattern'))
                        except ValueError as e:
                            error(e)
                    elif elem.tag == 'alias':
                        datetime_formats = Alias(_translate_alias(
                            ['datetime_formats'], elem.attrib['path'])
                        )

        # <numbers>

        number_symbols = data.setdefault('number_symbols', {})
        for elem in tree.findall('.//numbers/symbols/*'):
            if ('draft' in elem.attrib or 'alt' in elem.attrib):
                continue
            number_symbols[elem.tag] = text_type(elem.text)

        decimal_formats = data.setdefault('decimal_formats', {})
        for elem in tree.findall('.//decimalFormats/decimalFormatLength'):
            if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                    and elem.attrib.get('type') in decimal_formats:
                continue
            if elem.findall('./alias'):
                # TODO map the alias to its target
                continue
            pattern = text_type(elem.findtext('./decimalFormat/pattern'))
            decimal_formats[elem.attrib.get('type')] = \
                numbers.parse_pattern(pattern)

        scientific_formats = data.setdefault('scientific_formats', {})
        for elem in tree.findall('.//scientificFormats/scientificFormatLength'):
            if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                    and elem.attrib.get('type') in scientific_formats:
                continue
            pattern = text_type(elem.findtext('scientificFormat/pattern'))
            scientific_formats[elem.attrib.get('type')] = \
                numbers.parse_pattern(pattern)

        currency_formats = data.setdefault('currency_formats', {})
        for elem in tree.findall('.//currencyFormats/currencyFormatLength'):
            if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                    and elem.attrib.get('type') in currency_formats:
                continue
            pattern = text_type(elem.findtext('currencyFormat/pattern'))
            currency_formats[elem.attrib.get('type')] = \
                numbers.parse_pattern(pattern)

        percent_formats = data.setdefault('percent_formats', {})
        for elem in tree.findall('.//percentFormats/percentFormatLength'):
            if ('draft' in elem.attrib or 'alt' in elem.attrib) \
                    and elem.attrib.get('type') in percent_formats:
                continue
            pattern = text_type(elem.findtext('percentFormat/pattern'))
            percent_formats[elem.attrib.get('type')] = \
                numbers.parse_pattern(pattern)

        currency_names = data.setdefault('currency_names', {})
        currency_names_plural = data.setdefault('currency_names_plural', {})
        currency_symbols = data.setdefault('currency_symbols', {})
        for elem in tree.findall('.//currencies/currency'):
            code = elem.attrib['type']
            for name in elem.findall('displayName'):
                if ('draft' in name.attrib) and code in currency_names:
                    continue
                if 'count' in name.attrib:
                    currency_names_plural.setdefault(code, {})[
                        name.attrib['count']] = text_type(name.text)
                else:
                    currency_names[code] = text_type(name.text)
            # TODO: support choice patterns for currency symbol selection
            symbol = elem.find('symbol')
            if symbol is not None and 'draft' not in symbol.attrib \
                    and 'choice' not in symbol.attrib:
                currency_symbols[code] = text_type(symbol.text)

        # <units>

        unit_patterns = data.setdefault('unit_patterns', {})
        for elem in tree.findall('.//units/unit'):
            unit_type = elem.attrib['type']
            for pattern in elem.findall('unitPattern'):
                box = unit_type
                if 'alt' in pattern.attrib:
                    box += ':' + pattern.attrib['alt']
                unit_patterns.setdefault(box, {})[pattern.attrib['count']] = \
                    text_type(pattern.text)

        outfile = open(data_filename, 'wb')
        try:
            pickle.dump(data, outfile, 2)
        finally:
            outfile.close()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = make-release
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    make-release
    ~~~~~~~~~~~~

    Helper script that performs a release.  Does pretty much everything
    automatically for us.

    :copyright: (c) 2013 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
import os
import re
from datetime import datetime, date
from subprocess import Popen, PIPE

_date_clean_re = re.compile(r'(\d+)(st|nd|rd|th)')


def parse_changelog():
    with open('CHANGES') as f:
        lineiter = iter(f)
        for line in lineiter:
            match = re.search('^Version\s+(.*)', line.strip())
            if match is None:
                continue
            length = len(match.group(1))
            version = match.group(1).strip()
            if lineiter.next().count('-') != len(match.group(0)):
                continue
            while 1:
                change_info = lineiter.next().strip()
                if change_info:
                    break

            match = re.search(r'released on (\w+\s+\d+\w+\s+\d+)'
                              r'(?:, codename (.*))?(?i)', change_info)
            if match is None:
                continue

            datestr, codename = match.groups()
            return version, parse_date(datestr), codename


def bump_version(version):
    try:
        parts = map(int, version.split('.'))
    except ValueError:
        fail('Current version is not numeric')
    if parts[-1] != 0:
        parts[-1] += 1
    else:
        parts[0] += 1
    return '.'.join(map(str, parts))


def parse_date(string):
    string = _date_clean_re.sub(r'\1', string)
    return datetime.strptime(string, '%B %d %Y')


def set_filename_version(filename, version_number, pattern):
    changed = []
    def inject_version(match):
        before, old, after = match.groups()
        changed.append(True)
        return before + version_number + after
    with open(filename) as f:
        contents = re.sub(r"^(\s*%s\s*=\s*')(.+?)(')(?sm)" % pattern,
                          inject_version, f.read())

    if not changed:
        fail('Could not find %s in %s', pattern, filename)

    with open(filename, 'w') as f:
        f.write(contents)


def set_init_version(version):
    info('Setting __init__.py version to %s', version)
    set_filename_version('babel/__init__.py', version, '__version__')


def set_setup_version(version):
    info('Setting setup.py version to %s', version)
    set_filename_version('setup.py', version, 'version')


def build_and_upload():
    Popen([sys.executable, 'setup.py', 'release', 'sdist', 'upload']).wait()


def fail(message, *args):
    print >> sys.stderr, 'Error:', message % args
    sys.exit(1)


def info(message, *args):
    print >> sys.stderr, message % args


def get_git_tags():
    return set(Popen(['git', 'tag'], stdout=PIPE).communicate()[0].splitlines())


def git_is_clean():
    return Popen(['git', 'diff', '--quiet']).wait() == 0


def make_git_commit(message, *args):
    message = message % args
    Popen(['git', 'commit', '-am', message]).wait()


def make_git_tag(tag):
    info('Tagging "%s"', tag)
    Popen(['git', 'tag', tag]).wait()


def main():
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

    rv = parse_changelog()
    if rv is None:
        fail('Could not parse changelog')

    version, release_date, codename = rv
    dev_version = bump_version(version) + '-dev'

    info('Releasing %s (codename %s, release date %s)',
         version, codename, release_date.strftime('%d/%m/%Y'))
    tags = get_git_tags()

    if version in tags:
        fail('Version "%s" is already tagged', version)
    if release_date.date() != date.today():
        fail('Release date is not today (%s != %s)')

    if not git_is_clean():
        fail('You have uncommitted changes in git')

    set_init_version(version)
    set_setup_version(version)
    make_git_commit('Bump version number to %s', version)
    make_git_tag(version)
    build_and_upload()
    set_init_version(dev_version)
    set_setup_version(dev_version)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conftest
import os
import pytest


@pytest.fixture
def os_environ(monkeypatch):
    mock_environ = dict(os.environ)
    monkeypatch.setattr(os, 'environ', mock_environ)
    return mock_environ

########NEW FILE########
__FILENAME__ = file1
# -*- coding: utf-8 -*-
# file1.py for tests

from gettext import gettext as _
def foo():
    # TRANSLATOR: This will be a translator coment,
    # that will include several lines
    print _('bar')

########NEW FILE########
__FILENAME__ = file2
# -*- coding: utf-8 -*-
# file2.py for tests

from gettext import ngettext

def foo():
    # Note: This will have the TRANSLATOR: tag but shouldn't
    # be included on the extracted stuff
    print ngettext('foobar', 'foobars', 1)

########NEW FILE########
__FILENAME__ = this_wont_normally_be_here
# -*- coding: utf-8 -*-

# This file won't normally be in this directory.
# It IS only for tests

from gettext import ngettext

def foo():
    # Note: This will have the TRANSLATOR: tag but shouldn't
    # be included on the extracted stuff
    print ngettext('FooBar', 'FooBars', 1)

########NEW FILE########
__FILENAME__ = test_catalog
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import copy
import datetime
import unittest

from babel.dates import format_datetime, UTC
from babel.messages import catalog
from babel.util import FixedOffsetTimezone


class MessageTestCase(unittest.TestCase):

    def test_python_format(self):
        assert catalog.PYTHON_FORMAT.search('foo %d bar')
        assert catalog.PYTHON_FORMAT.search('foo %s bar')
        assert catalog.PYTHON_FORMAT.search('foo %r bar')
        assert catalog.PYTHON_FORMAT.search('foo %(name).1f')
        assert catalog.PYTHON_FORMAT.search('foo %(name)3.3f')
        assert catalog.PYTHON_FORMAT.search('foo %(name)3f')
        assert catalog.PYTHON_FORMAT.search('foo %(name)06d')
        assert catalog.PYTHON_FORMAT.search('foo %(name)Li')
        assert catalog.PYTHON_FORMAT.search('foo %(name)#d')
        assert catalog.PYTHON_FORMAT.search('foo %(name)-4.4hs')
        assert catalog.PYTHON_FORMAT.search('foo %(name)*.3f')
        assert catalog.PYTHON_FORMAT.search('foo %(name).*f')
        assert catalog.PYTHON_FORMAT.search('foo %(name)3.*f')
        assert catalog.PYTHON_FORMAT.search('foo %(name)*.*f')
        assert catalog.PYTHON_FORMAT.search('foo %()s')

    def test_translator_comments(self):
        mess = catalog.Message('foo', user_comments=['Comment About `foo`'])
        self.assertEqual(mess.user_comments, ['Comment About `foo`'])
        mess = catalog.Message('foo',
                               auto_comments=['Comment 1 About `foo`',
                                         'Comment 2 About `foo`'])
        self.assertEqual(mess.auto_comments, ['Comment 1 About `foo`',
                                         'Comment 2 About `foo`'])

    def test_clone_message_object(self):
        msg = catalog.Message('foo', locations=[('foo.py', 42)])
        clone = msg.clone()
        clone.locations.append(('bar.py', 42))
        self.assertEqual(msg.locations, [('foo.py', 42)])
        msg.flags.add('fuzzy')
        assert not clone.fuzzy and msg.fuzzy


class CatalogTestCase(unittest.TestCase):
    def test_add_returns_message_instance(self):
        cat = catalog.Catalog()
        message = cat.add('foo')
        self.assertEquals('foo', message.id)

    def test_two_messages_with_same_singular(self):
        cat = catalog.Catalog()
        cat.add('foo')
        cat.add(('foo', 'foos'))
        self.assertEqual(1, len(cat))

    def test_duplicate_auto_comment(self):
        cat = catalog.Catalog()
        cat.add('foo', auto_comments=['A comment'])
        cat.add('foo', auto_comments=['A comment', 'Another comment'])
        self.assertEqual(['A comment', 'Another comment'],
                         cat['foo'].auto_comments)

    def test_duplicate_user_comment(self):
        cat = catalog.Catalog()
        cat.add('foo', user_comments=['A comment'])
        cat.add('foo', user_comments=['A comment', 'Another comment'])
        self.assertEqual(['A comment', 'Another comment'],
                         cat['foo'].user_comments)

    def test_duplicate_location(self):
        cat = catalog.Catalog()
        cat.add('foo', locations=[('foo.py', 1)])
        cat.add('foo', locations=[('foo.py', 1)])
        self.assertEqual([('foo.py', 1)], cat['foo'].locations)

    def test_update_message_changed_to_plural(self):
        cat = catalog.Catalog()
        cat.add(u'foo', u'Voh')
        tmpl = catalog.Catalog()
        tmpl.add((u'foo', u'foos'))
        cat.update(tmpl)
        self.assertEqual((u'Voh', ''), cat['foo'].string)
        assert cat['foo'].fuzzy

    def test_update_message_changed_to_simple(self):
        cat = catalog.Catalog()
        cat.add((u'foo' u'foos'), (u'Voh', u'Vöhs'))
        tmpl = catalog.Catalog()
        tmpl.add(u'foo')
        cat.update(tmpl)
        self.assertEqual(u'Voh', cat['foo'].string)
        assert cat['foo'].fuzzy

    def test_update_message_updates_comments(self):
        cat = catalog.Catalog()
        cat[u'foo'] = catalog.Message('foo', locations=[('main.py', 5)])
        self.assertEqual(cat[u'foo'].auto_comments, [])
        self.assertEqual(cat[u'foo'].user_comments, [])
        # Update cat[u'foo'] with a new location and a comment
        cat[u'foo'] = catalog.Message('foo', locations=[('main.py', 7)],
                                      user_comments=['Foo Bar comment 1'])
        self.assertEqual(cat[u'foo'].user_comments, ['Foo Bar comment 1'])
        # now add yet another location with another comment
        cat[u'foo'] = catalog.Message('foo', locations=[('main.py', 9)],
                                      auto_comments=['Foo Bar comment 2'])
        self.assertEqual(cat[u'foo'].auto_comments, ['Foo Bar comment 2'])

    def test_update_fuzzy_matching_with_case_change(self):
        cat = catalog.Catalog()
        cat.add('foo', 'Voh')
        cat.add('bar', 'Bahr')
        tmpl = catalog.Catalog()
        tmpl.add('Foo')
        cat.update(tmpl)
        self.assertEqual(1, len(cat.obsolete))
        assert 'foo' not in cat

        self.assertEqual('Voh', cat['Foo'].string)
        self.assertEqual(True, cat['Foo'].fuzzy)

    def test_update_fuzzy_matching_with_char_change(self):
        cat = catalog.Catalog()
        cat.add('fo', 'Voh')
        cat.add('bar', 'Bahr')
        tmpl = catalog.Catalog()
        tmpl.add('foo')
        cat.update(tmpl)
        self.assertEqual(1, len(cat.obsolete))
        assert 'fo' not in cat

        self.assertEqual('Voh', cat['foo'].string)
        self.assertEqual(True, cat['foo'].fuzzy)

    def test_update_fuzzy_matching_no_msgstr(self):
        cat = catalog.Catalog()
        cat.add('fo', '')
        tmpl = catalog.Catalog()
        tmpl.add('fo')
        tmpl.add('foo')
        cat.update(tmpl)
        assert 'fo' in cat
        assert 'foo' in cat

        self.assertEqual('', cat['fo'].string)
        self.assertEqual(False, cat['fo'].fuzzy)
        self.assertEqual(None, cat['foo'].string)
        self.assertEqual(False, cat['foo'].fuzzy)

    def test_update_fuzzy_matching_with_new_context(self):
        cat = catalog.Catalog()
        cat.add('foo', 'Voh')
        cat.add('bar', 'Bahr')
        tmpl = catalog.Catalog()
        tmpl.add('Foo', context='Menu')
        cat.update(tmpl)
        self.assertEqual(1, len(cat.obsolete))
        assert 'foo' not in cat

        message = cat.get('Foo', 'Menu')
        self.assertEqual('Voh', message.string)
        self.assertEqual(True, message.fuzzy)
        self.assertEqual('Menu', message.context)

    def test_update_fuzzy_matching_with_changed_context(self):
        cat = catalog.Catalog()
        cat.add('foo', 'Voh', context='Menu|File')
        cat.add('bar', 'Bahr', context='Menu|File')
        tmpl = catalog.Catalog()
        tmpl.add('Foo', context='Menu|Edit')
        cat.update(tmpl)
        self.assertEqual(1, len(cat.obsolete))
        assert cat.get('Foo', 'Menu|File') is None

        message = cat.get('Foo', 'Menu|Edit')
        self.assertEqual('Voh', message.string)
        self.assertEqual(True, message.fuzzy)
        self.assertEqual('Menu|Edit', message.context)

    def test_update_fuzzy_matching_no_cascading(self):
        cat = catalog.Catalog()
        cat.add('fo', 'Voh')
        cat.add('foo', 'Vohe')
        tmpl = catalog.Catalog()
        tmpl.add('fo')
        tmpl.add('foo')
        tmpl.add('fooo')
        cat.update(tmpl)
        assert 'fo' in cat
        assert 'foo' in cat

        self.assertEqual('Voh', cat['fo'].string)
        self.assertEqual(False, cat['fo'].fuzzy)
        self.assertEqual('Vohe', cat['foo'].string)
        self.assertEqual(False, cat['foo'].fuzzy)
        self.assertEqual('Vohe', cat['fooo'].string)
        self.assertEqual(True, cat['fooo'].fuzzy)

    def test_update_without_fuzzy_matching(self):
        cat = catalog.Catalog()
        cat.add('fo', 'Voh')
        cat.add('bar', 'Bahr')
        tmpl = catalog.Catalog()
        tmpl.add('foo')
        cat.update(tmpl, no_fuzzy_matching=True)
        self.assertEqual(2, len(cat.obsolete))

    def test_fuzzy_matching_regarding_plurals(self):
        cat = catalog.Catalog()
        cat.add(('foo', 'foh'), ('foo', 'foh'))
        ru = copy.copy(cat)
        ru.locale = 'ru_RU'
        ru.update(cat)
        self.assertEqual(True, ru['foo'].fuzzy)
        ru = copy.copy(cat)
        ru.locale = 'ru_RU'
        ru['foo'].string = ('foh', 'fohh', 'fohhh')
        ru.update(cat)
        self.assertEqual(False, ru['foo'].fuzzy)

    def test_update_no_template_mutation(self):
        tmpl = catalog.Catalog()
        tmpl.add('foo')
        cat1 = catalog.Catalog()
        cat1.add('foo', 'Voh')
        cat1.update(tmpl)
        cat2 = catalog.Catalog()
        cat2.update(tmpl)

        self.assertEqual(None, cat2['foo'].string)
        self.assertEqual(False, cat2['foo'].fuzzy)

    def test_update_po_updates_pot_creation_date(self):
        template = catalog.Catalog()
        localized_catalog = copy.deepcopy(template)
        localized_catalog.locale = 'de_DE'
        self.assertNotEqual(template.mime_headers,
                            localized_catalog.mime_headers)
        self.assertEqual(template.creation_date,
                         localized_catalog.creation_date)
        template.creation_date = datetime.datetime.now() - \
                                                datetime.timedelta(minutes=5)
        localized_catalog.update(template)
        self.assertEqual(template.creation_date,
                         localized_catalog.creation_date)

    def test_update_po_keeps_po_revision_date(self):
        template = catalog.Catalog()
        localized_catalog = copy.deepcopy(template)
        localized_catalog.locale = 'de_DE'
        fake_rev_date = datetime.datetime.now() - datetime.timedelta(days=5)
        localized_catalog.revision_date = fake_rev_date
        self.assertNotEqual(template.mime_headers,
                            localized_catalog.mime_headers)
        self.assertEqual(template.creation_date,
                         localized_catalog.creation_date)
        template.creation_date = datetime.datetime.now() - \
                                                datetime.timedelta(minutes=5)
        localized_catalog.update(template)
        self.assertEqual(localized_catalog.revision_date, fake_rev_date)

    def test_stores_datetime_correctly(self):
        localized = catalog.Catalog()
        localized.locale = 'de_DE'
        localized[''] = catalog.Message('',
                       "POT-Creation-Date: 2009-03-09 15:47-0700\n" +
                       "PO-Revision-Date: 2009-03-09 15:47-0700\n")
        for key, value in localized.mime_headers:
            if key in ('POT-Creation-Date', 'PO-Revision-Date'):
                self.assertEqual(value, '2009-03-09 15:47-0700')

    def test_mime_headers_contain_same_information_as_attributes(self):
        cat = catalog.Catalog()
        cat[''] = catalog.Message('',
                      "Last-Translator: Foo Bar <foo.bar@example.com>\n" +
                      "Language-Team: de <de@example.com>\n" +
                      "POT-Creation-Date: 2009-03-01 11:20+0200\n" +
                      "PO-Revision-Date: 2009-03-09 15:47-0700\n")
        self.assertEqual(None, cat.locale)
        mime_headers = dict(cat.mime_headers)

        self.assertEqual('Foo Bar <foo.bar@example.com>', cat.last_translator)
        self.assertEqual('Foo Bar <foo.bar@example.com>',
                         mime_headers['Last-Translator'])

        self.assertEqual('de <de@example.com>', cat.language_team)
        self.assertEqual('de <de@example.com>', mime_headers['Language-Team'])

        dt = datetime.datetime(2009, 3, 9, 15, 47, tzinfo=FixedOffsetTimezone(-7 * 60))
        self.assertEqual(dt, cat.revision_date)
        formatted_dt = format_datetime(dt, 'yyyy-MM-dd HH:mmZ', locale='en')
        self.assertEqual(formatted_dt, mime_headers['PO-Revision-Date'])


def test_message_fuzzy():
    assert not catalog.Message('foo').fuzzy
    msg = catalog.Message('foo', 'foo', flags=['fuzzy'])
    assert msg.fuzzy
    assert msg.id == 'foo'

def test_message_pluralizable():
    assert not catalog.Message('foo').pluralizable
    assert catalog.Message(('foo', 'bar')).pluralizable

def test_message_python_format():
    assert catalog.Message('foo %(name)s bar').python_format
    assert catalog.Message(('foo %(name)s', 'foo %(name)s')).python_format


def test_catalog():
    cat = catalog.Catalog(project='Foobar', version='1.0',
                          copyright_holder='Foo Company')
    assert cat.header_comment == (
        '# Translations template for Foobar.\n'
        '# Copyright (C) %(year)d Foo Company\n'
        '# This file is distributed under the same '
            'license as the Foobar project.\n'
        '# FIRST AUTHOR <EMAIL@ADDRESS>, %(year)d.\n'
        '#') % {'year': datetime.date.today().year}

    cat = catalog.Catalog(project='Foobar', version='1.0',
                          copyright_holder='Foo Company')
    cat.header_comment = (
        '# The POT for my really cool PROJECT project.\n'
        '# Copyright (C) 1990-2003 ORGANIZATION\n'
        '# This file is distributed under the same license as the PROJECT\n'
        '# project.\n'
        '#\n')
    assert cat.header_comment == (
        '# The POT for my really cool Foobar project.\n'
        '# Copyright (C) 1990-2003 Foo Company\n'
        '# This file is distributed under the same license as the Foobar\n'
        '# project.\n'
        '#\n')


def test_catalog_mime_headers():
    created = datetime.datetime(1990, 4, 1, 15, 30, tzinfo=UTC)
    cat = catalog.Catalog(project='Foobar', version='1.0',
                          creation_date=created)
    assert cat.mime_headers == [
        ('Project-Id-Version', 'Foobar 1.0'),
        ('Report-Msgid-Bugs-To', 'EMAIL@ADDRESS'),
        ('POT-Creation-Date', '1990-04-01 15:30+0000'),
        ('PO-Revision-Date', 'YEAR-MO-DA HO:MI+ZONE'),
        ('Last-Translator', 'FULL NAME <EMAIL@ADDRESS>'),
        ('Language-Team', 'LANGUAGE <LL@li.org>'),
        ('MIME-Version', '1.0'),
        ('Content-Type', 'text/plain; charset=utf-8'),
        ('Content-Transfer-Encoding', '8bit'),
        ('Generated-By', 'Babel %s\n' % catalog.VERSION),
    ]


def test_catalog_mime_headers_set_locale():
    created = datetime.datetime(1990, 4, 1, 15, 30, tzinfo=UTC)
    revised = datetime.datetime(1990, 8, 3, 12, 0, tzinfo=UTC)
    cat = catalog.Catalog(locale='de_DE', project='Foobar', version='1.0',
                          creation_date=created, revision_date=revised,
                          last_translator='John Doe <jd@example.com>',
                          language_team='de_DE <de@example.com>')
    assert cat.mime_headers == [
        ('Project-Id-Version', 'Foobar 1.0'),
        ('Report-Msgid-Bugs-To', 'EMAIL@ADDRESS'),
        ('POT-Creation-Date', '1990-04-01 15:30+0000'),
        ('PO-Revision-Date', '1990-08-03 12:00+0000'),
        ('Last-Translator', 'John Doe <jd@example.com>'),
        ('Language-Team', 'de_DE <de@example.com>'),
        ('Plural-Forms', 'nplurals=2; plural=(n != 1)'),
        ('MIME-Version', '1.0'),
        ('Content-Type', 'text/plain; charset=utf-8'),
        ('Content-Transfer-Encoding', '8bit'),
        ('Generated-By', 'Babel %s\n' % catalog.VERSION),
    ]


def test_catalog_num_plurals():
    assert catalog.Catalog(locale='en').num_plurals == 2
    assert catalog.Catalog(locale='ga').num_plurals == 3


def test_catalog_plural_expr():
    assert catalog.Catalog(locale='en').plural_expr == '(n != 1)'
    assert (catalog.Catalog(locale='ga').plural_expr
            == '(n==1 ? 0 : n==2 ? 1 : 2)')


def test_catalog_plural_forms():
    assert (catalog.Catalog(locale='en').plural_forms
            == 'nplurals=2; plural=(n != 1)')
    assert (catalog.Catalog(locale='pt_BR').plural_forms
            == 'nplurals=2; plural=(n > 1)')


def test_catalog_setitem():
    cat = catalog.Catalog()
    cat[u'foo'] = catalog.Message(u'foo')
    assert cat[u'foo'].id == 'foo'

    cat = catalog.Catalog()
    cat[u'foo'] = catalog.Message(u'foo', locations=[('main.py', 1)])
    assert cat[u'foo'].locations == [('main.py', 1)]
    cat[u'foo'] = catalog.Message(u'foo', locations=[('utils.py', 5)])
    assert cat[u'foo'].locations == [('main.py', 1), ('utils.py', 5)]


def test_catalog_add():
    cat = catalog.Catalog()
    foo = cat.add(u'foo')
    assert foo.id == 'foo'
    assert cat[u'foo'] is foo


def test_catalog_update():
    template = catalog.Catalog()
    template.add('green', locations=[('main.py', 99)])
    template.add('blue', locations=[('main.py', 100)])
    template.add(('salad', 'salads'), locations=[('util.py', 42)])
    cat = catalog.Catalog(locale='de_DE')
    cat.add('blue', u'blau', locations=[('main.py', 98)])
    cat.add('head', u'Kopf', locations=[('util.py', 33)])
    cat.add(('salad', 'salads'), (u'Salat', u'Salate'),
                locations=[('util.py', 38)])

    cat.update(template)
    assert len(cat) == 3

    msg1 = cat['green']
    msg1.string
    assert msg1.locations == [('main.py', 99)]

    msg2 = cat['blue']
    assert msg2.string == u'blau'
    assert msg2.locations == [('main.py', 100)]

    msg3 = cat['salad']
    assert msg3.string == (u'Salat', u'Salate')
    assert msg3.locations == [('util.py', 42)]

    assert not 'head' in cat
    assert list(cat.obsolete.values())[0].id == 'head'


def test_datetime_parsing():
    val1 = catalog._parse_datetime_header('2006-06-28 23:24+0200')
    assert val1.year == 2006
    assert val1.month == 6
    assert val1.day == 28
    assert val1.tzinfo.zone == 'Etc/GMT+120'

    val2 = catalog._parse_datetime_header('2006-06-28 23:24')
    assert val2.year == 2006
    assert val2.month == 6
    assert val2.day == 28
    assert val2.tzinfo is None

########NEW FILE########
__FILENAME__ = test_checkers
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

from datetime import datetime
import time
import unittest

from babel import __version__ as VERSION
from babel.core import Locale, UnknownLocaleError
from babel.dates import format_datetime
from babel.messages import checkers
from babel.messages.plurals import PLURALS
from babel.messages.pofile import read_po
from babel.util import LOCALTZ
from babel._compat import BytesIO


class CheckersTestCase(unittest.TestCase):
    # the last msgstr[idx] is always missing except for singular plural forms

    def test_1_num_plurals_checkers(self):
        for _locale in [p for p in PLURALS if PLURALS[p][0] == 1]:
            try:
                locale = Locale.parse(_locale)
            except UnknownLocaleError:
                # Just an alias? Not what we're testing here, let's continue
                continue
            po_file = (u"""\
# %(english_name)s translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\\n"
"PO-Revision-Date: %(date)s\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: %(locale)s <LL@li.org>\n"
"Plural-Forms: nplurals=%(num_plurals)s; plural=%(plural_expr)s\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=utf-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Generated-By: Babel %(version)s\\n"

#. This will be a translator comment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""

""" % dict(locale       = _locale,
           english_name = locale.english_name,
           version      = VERSION,
           year         = time.strftime('%Y'),
           date         = format_datetime(datetime.now(LOCALTZ),
                                          'yyyy-MM-dd HH:mmZ',
                                          tzinfo=LOCALTZ, locale=_locale),
           num_plurals  = PLURALS[_locale][0],
           plural_expr  = PLURALS[_locale][0])).encode('utf-8')

            # This test will fail for revisions <= 406 because so far
            # catalog.num_plurals was neglected
            catalog = read_po(BytesIO(po_file), _locale)
            message = catalog['foobar']
            checkers.num_plurals(catalog, message)

    def test_2_num_plurals_checkers(self):
        # in this testcase we add an extra msgstr[idx], we should be
        # disregarding it
        for _locale in [p for p in PLURALS if PLURALS[p][0] == 2]:
            if _locale in ['nn', 'no']:
                _locale = 'nn_NO'
                num_plurals  = PLURALS[_locale.split('_')[0]][0]
                plural_expr  = PLURALS[_locale.split('_')[0]][1]
            else:
                num_plurals  = PLURALS[_locale][0]
                plural_expr  = PLURALS[_locale][1]
            try:
                locale = Locale(_locale)
                date = format_datetime(datetime.now(LOCALTZ),
                                       'yyyy-MM-dd HH:mmZ',
                                       tzinfo=LOCALTZ, locale=_locale)
            except UnknownLocaleError:
                # Just an alias? Not what we're testing here, let's continue
                continue
            po_file = (u"""\
# %(english_name)s translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\\n"
"PO-Revision-Date: %(date)s\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: %(locale)s <LL@li.org>\\n"
"Plural-Forms: nplurals=%(num_plurals)s; plural=%(plural_expr)s\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=utf-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Generated-By: Babel %(version)s\\n"

#. This will be a translator comment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""
msgstr[2] ""

""" % dict(locale       = _locale,
           english_name = locale.english_name,
           version      = VERSION,
           year         = time.strftime('%Y'),
           date         = date,
           num_plurals  = num_plurals,
           plural_expr  = plural_expr)).encode('utf-8')
            # we should be adding the missing msgstr[0]

            # This test will fail for revisions <= 406 because so far
            # catalog.num_plurals was neglected
            catalog = read_po(BytesIO(po_file), _locale)
            message = catalog['foobar']
            checkers.num_plurals(catalog, message)

    def test_3_num_plurals_checkers(self):
        for _locale in [p for p in PLURALS if PLURALS[p][0] == 3]:
            po_file = (r"""\
# %(english_name)s translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: %(locale)s <LL@li.org>\n"
"Plural-Forms: nplurals=%(num_plurals)s; plural=%(plural_expr)s\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator comment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

""" % dict(locale       = _locale,
           english_name = Locale.parse(_locale).english_name,
           version      = VERSION,
           year         = time.strftime('%Y'),
           date         = format_datetime(datetime.now(LOCALTZ),
                                          'yyyy-MM-dd HH:mmZ',
                                          tzinfo=LOCALTZ, locale=_locale),
           num_plurals  = PLURALS[_locale][0],
           plural_expr  = PLURALS[_locale][0])).encode('utf-8')

            # This test will fail for revisions <= 406 because so far
            # catalog.num_plurals was neglected
            catalog = read_po(BytesIO(po_file), _locale)
            message = catalog['foobar']
            checkers.num_plurals(catalog, message)

    def test_4_num_plurals_checkers(self):
        for _locale in [p for p in PLURALS if PLURALS[p][0] == 4]:
            po_file = (r"""\
# %(english_name)s translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: %(locale)s <LL@li.org>\n"
"Plural-Forms: nplurals=%(num_plurals)s; plural=%(plural_expr)s\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator comment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""
msgstr[2] ""

""" % dict(locale       = _locale,
           english_name = Locale.parse(_locale).english_name,
           version      = VERSION,
           year         = time.strftime('%Y'),
           date         = format_datetime(datetime.now(LOCALTZ),
                                          'yyyy-MM-dd HH:mmZ',
                                          tzinfo=LOCALTZ, locale=_locale),
           num_plurals  = PLURALS[_locale][0],
           plural_expr  = PLURALS[_locale][0])).encode('utf-8')

            # This test will fail for revisions <= 406 because so far
            # catalog.num_plurals was neglected
            catalog = read_po(BytesIO(po_file), _locale)
            message = catalog['foobar']
            checkers.num_plurals(catalog, message)

    def test_5_num_plurals_checkers(self):
        for _locale in [p for p in PLURALS if PLURALS[p][0] == 5]:
            po_file = (r"""\
# %(english_name)s translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: %(locale)s <LL@li.org>\n"
"Plural-Forms: nplurals=%(num_plurals)s; plural=%(plural_expr)s\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator comment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""
msgstr[2] ""
msgstr[3] ""

""" % dict(locale       = _locale,
           english_name = Locale.parse(_locale).english_name,
           version      = VERSION,
           year         = time.strftime('%Y'),
           date         = format_datetime(datetime.now(LOCALTZ),
                                          'yyyy-MM-dd HH:mmZ',
                                          tzinfo=LOCALTZ, locale=_locale),
           num_plurals  = PLURALS[_locale][0],
           plural_expr  = PLURALS[_locale][0])).encode('utf-8')

            # This test will fail for revisions <= 406 because so far
            # catalog.num_plurals was neglected
            catalog = read_po(BytesIO(po_file), _locale)
            message = catalog['foobar']
            checkers.num_plurals(catalog, message)

    def test_6_num_plurals_checkers(self):
        for _locale in [p for p in PLURALS if PLURALS[p][0] == 6]:
            po_file = (r"""\
# %(english_name)s translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: %(locale)s <LL@li.org>\n"
"Plural-Forms: nplurals=%(num_plurals)s; plural=%(plural_expr)s\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator comment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""
msgstr[2] ""
msgstr[3] ""
msgstr[4] ""

""" % dict(locale       = _locale,
           english_name = Locale.parse(_locale).english_name,
           version      = VERSION,
           year         = time.strftime('%Y'),
           date         = format_datetime(datetime.now(LOCALTZ),
                                          'yyyy-MM-dd HH:mmZ',
                                          tzinfo=LOCALTZ, locale=_locale),
           num_plurals  = PLURALS[_locale][0],
           plural_expr  = PLURALS[_locale][0])).encode('utf-8')

            # This test will fail for revisions <= 406 because so far
            # catalog.num_plurals was neglected
            catalog = read_po(BytesIO(po_file), _locale)
            message = catalog['foobar']
            checkers.num_plurals(catalog, message)

########NEW FILE########
__FILENAME__ = test_extract
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import codecs
import sys
import unittest

from babel.messages import extract
from babel._compat import BytesIO, StringIO


class ExtractPythonTestCase(unittest.TestCase):

    def test_nested_calls(self):
        buf = BytesIO(b"""\
msg1 = _(i18n_arg.replace(r'\"', '"'))
msg2 = ungettext(i18n_arg.replace(r'\"', '"'), multi_arg.replace(r'\"', '"'), 2)
msg3 = ungettext("Babel", multi_arg.replace(r'\"', '"'), 2)
msg4 = ungettext(i18n_arg.replace(r'\"', '"'), "Babels", 2)
msg5 = ungettext('bunny', 'bunnies', random.randint(1, 2))
msg6 = ungettext(arg0, 'bunnies', random.randint(1, 2))
msg7 = _(hello.there)
msg8 = gettext('Rabbit')
msg9 = dgettext('wiki', model.addPage())
msg10 = dngettext(getDomain(), 'Page', 'Pages', 3)
""")
        messages = list(extract.extract_python(buf,
                                               extract.DEFAULT_KEYWORDS.keys(),
                                               [], {}))
        self.assertEqual([
                (1, '_', None, []),
                (2, 'ungettext', (None, None, None), []),
                (3, 'ungettext', (u'Babel', None, None), []),
                (4, 'ungettext', (None, u'Babels', None), []),
                (5, 'ungettext', (u'bunny', u'bunnies', None), []),
                (6, 'ungettext', (None, u'bunnies', None), []),
                (7, '_', None, []),
                (8, 'gettext', u'Rabbit', []),
                (9, 'dgettext', (u'wiki', None), []),
                (10, 'dngettext', (None, u'Page', u'Pages', None), [])],
                         messages)

    def test_nested_comments(self):
        buf = BytesIO(b"""\
msg = ngettext('pylon',  # TRANSLATORS: shouldn't be
               'pylons', # TRANSLATORS: seeing this
               count)
""")
        messages = list(extract.extract_python(buf, ('ngettext',),
                                               ['TRANSLATORS:'], {}))
        self.assertEqual([(1, 'ngettext', (u'pylon', u'pylons', None), [])],
                         messages)

    def test_comments_with_calls_that_spawn_multiple_lines(self):
        buf = BytesIO(b"""\
# NOTE: This Comment SHOULD Be Extracted
add_notice(req, ngettext("Catalog deleted.",
                         "Catalogs deleted.", len(selected)))

# NOTE: This Comment SHOULD Be Extracted
add_notice(req, _("Locale deleted."))


# NOTE: This Comment SHOULD Be Extracted
add_notice(req, ngettext("Foo deleted.", "Foos deleted.", len(selected)))

# NOTE: This Comment SHOULD Be Extracted
# NOTE: And This One Too
add_notice(req, ngettext("Bar deleted.",
                         "Bars deleted.", len(selected)))
""")
        messages = list(extract.extract_python(buf, ('ngettext','_'), ['NOTE:'],

                                               {'strip_comment_tags':False}))
        self.assertEqual((6, '_', 'Locale deleted.',
                          [u'NOTE: This Comment SHOULD Be Extracted']),
                         messages[1])
        self.assertEqual((10, 'ngettext', (u'Foo deleted.', u'Foos deleted.',
                                           None),
                          [u'NOTE: This Comment SHOULD Be Extracted']),
                         messages[2])
        self.assertEqual((3, 'ngettext',
                           (u'Catalog deleted.',
                            u'Catalogs deleted.', None),
                           [u'NOTE: This Comment SHOULD Be Extracted']),
                         messages[0])
        self.assertEqual((15, 'ngettext', (u'Bar deleted.', u'Bars deleted.',
                                           None),
                          [u'NOTE: This Comment SHOULD Be Extracted',
                           u'NOTE: And This One Too']),
                         messages[3])

    def test_declarations(self):
        buf = BytesIO(b"""\
class gettext(object):
    pass
def render_body(context,x,y=_('Page arg 1'),z=_('Page arg 2'),**pageargs):
    pass
def ngettext(y='arg 1',z='arg 2',**pageargs):
    pass
class Meta:
    verbose_name = _('log entry')
""")
        messages = list(extract.extract_python(buf,
                                               extract.DEFAULT_KEYWORDS.keys(),
                                               [], {}))
        self.assertEqual([(3, '_', u'Page arg 1', []),
                          (3, '_', u'Page arg 2', []),
                          (8, '_', u'log entry', [])],
                         messages)

    def test_multiline(self):
        buf = BytesIO(b"""\
msg1 = ngettext('pylon',
                'pylons', count)
msg2 = ngettext('elvis',
                'elvises',
                 count)
""")
        messages = list(extract.extract_python(buf, ('ngettext',), [], {}))
        self.assertEqual([(1, 'ngettext', (u'pylon', u'pylons', None), []),
                          (3, 'ngettext', (u'elvis', u'elvises', None), [])],
                         messages)

    def test_triple_quoted_strings(self):
        buf = BytesIO(b"""\
msg1 = _('''pylons''')
msg2 = ngettext(r'''elvis''', \"\"\"elvises\"\"\", count)
msg2 = ngettext(\"\"\"elvis\"\"\", 'elvises', count)
""")
        messages = list(extract.extract_python(buf,
                                               extract.DEFAULT_KEYWORDS.keys(),
                                               [], {}))
        self.assertEqual([(1, '_', (u'pylons'), []),
                          (2, 'ngettext', (u'elvis', u'elvises', None), []),
                          (3, 'ngettext', (u'elvis', u'elvises', None), [])],
                         messages)

    def test_multiline_strings(self):
        buf = BytesIO(b"""\
_('''This module provides internationalization and localization
support for your Python programs by providing an interface to the GNU
gettext message catalog library.''')
""")
        messages = list(extract.extract_python(buf,
                                               extract.DEFAULT_KEYWORDS.keys(),
                                               [], {}))
        self.assertEqual(
            [(1, '_',
              u'This module provides internationalization and localization\n'
              'support for your Python programs by providing an interface to '
              'the GNU\ngettext message catalog library.', [])],
            messages)

    def test_concatenated_strings(self):
        buf = BytesIO(b"""\
foobar = _('foo' 'bar')
""")
        messages = list(extract.extract_python(buf,
                                               extract.DEFAULT_KEYWORDS.keys(),
                                               [], {}))
        self.assertEqual(u'foobar', messages[0][2])

    def test_unicode_string_arg(self):
        buf = BytesIO(b"msg = _(u'Foo Bar')")
        messages = list(extract.extract_python(buf, ('_',), [], {}))
        self.assertEqual(u'Foo Bar', messages[0][2])

    def test_comment_tag(self):
        buf = BytesIO(b"""
# NOTE: A translation comment
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Foo Bar', messages[0][2])
        self.assertEqual([u'NOTE: A translation comment'], messages[0][3])

    def test_comment_tag_multiline(self):
        buf = BytesIO(b"""
# NOTE: A translation comment
# with a second line
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Foo Bar', messages[0][2])
        self.assertEqual([u'NOTE: A translation comment', u'with a second line'],
                         messages[0][3])

    def test_translator_comments_with_previous_non_translator_comments(self):
        buf = BytesIO(b"""
# This shouldn't be in the output
# because it didn't start with a comment tag
# NOTE: A translation comment
# with a second line
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Foo Bar', messages[0][2])
        self.assertEqual([u'NOTE: A translation comment', u'with a second line'],
                         messages[0][3])

    def test_comment_tags_not_on_start_of_comment(self):
        buf = BytesIO(b"""
# This shouldn't be in the output
# because it didn't start with a comment tag
# do NOTE: this will not be a translation comment
# NOTE: This one will be
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Foo Bar', messages[0][2])
        self.assertEqual([u'NOTE: This one will be'], messages[0][3])

    def test_multiple_comment_tags(self):
        buf = BytesIO(b"""
# NOTE1: A translation comment for tag1
# with a second line
msg = _(u'Foo Bar1')

# NOTE2: A translation comment for tag2
msg = _(u'Foo Bar2')
""")
        messages = list(extract.extract_python(buf, ('_',),
                                               ['NOTE1:', 'NOTE2:'], {}))
        self.assertEqual(u'Foo Bar1', messages[0][2])
        self.assertEqual([u'NOTE1: A translation comment for tag1',
                          u'with a second line'], messages[0][3])
        self.assertEqual(u'Foo Bar2', messages[1][2])
        self.assertEqual([u'NOTE2: A translation comment for tag2'], messages[1][3])

    def test_two_succeeding_comments(self):
        buf = BytesIO(b"""
# NOTE: one
# NOTE: two
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Foo Bar', messages[0][2])
        self.assertEqual([u'NOTE: one', u'NOTE: two'], messages[0][3])

    def test_invalid_translator_comments(self):
        buf = BytesIO(b"""
# NOTE: this shouldn't apply to any messages
hello = 'there'

msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Foo Bar', messages[0][2])
        self.assertEqual([], messages[0][3])

    def test_invalid_translator_comments2(self):
        buf = BytesIO(b"""
# NOTE: Hi!
hithere = _('Hi there!')

# NOTE: you should not be seeing this in the .po
rows = [[v for v in range(0,10)] for row in range(0,10)]

# this (NOTE:) should not show up either
hello = _('Hello')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Hi there!', messages[0][2])
        self.assertEqual([u'NOTE: Hi!'], messages[0][3])
        self.assertEqual(u'Hello', messages[1][2])
        self.assertEqual([], messages[1][3])

    def test_invalid_translator_comments3(self):
        buf = BytesIO(b"""
# NOTE: Hi,

# there!
hithere = _('Hi there!')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Hi there!', messages[0][2])
        self.assertEqual([], messages[0][3])

    def test_comment_tag_with_leading_space(self):
        buf = BytesIO(b"""
  #: A translation comment
  #: with leading spaces
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), [':'], {}))
        self.assertEqual(u'Foo Bar', messages[0][2])
        self.assertEqual([u': A translation comment', u': with leading spaces'],
                         messages[0][3])

    def test_different_signatures(self):
        buf = BytesIO(b"""
foo = _('foo', 'bar')
n = ngettext('hello', 'there', n=3)
n = ngettext(n=3, 'hello', 'there')
n = ngettext(n=3, *messages)
n = ngettext()
n = ngettext('foo')
""")
        messages = list(extract.extract_python(buf, ('_', 'ngettext'), [], {}))
        self.assertEqual((u'foo', u'bar'), messages[0][2])
        self.assertEqual((u'hello', u'there', None), messages[1][2])
        self.assertEqual((None, u'hello', u'there'), messages[2][2])
        self.assertEqual((None, None), messages[3][2])
        self.assertEqual(None, messages[4][2])
        self.assertEqual(('foo'), messages[5][2])

    def test_utf8_message(self):
        buf = BytesIO(u"""
# NOTE: hello
msg = _('Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'],
                                               {'encoding': 'utf-8'}))
        self.assertEqual(u'Bonjour à tous', messages[0][2])
        self.assertEqual([u'NOTE: hello'], messages[0][3])

    def test_utf8_message_with_magic_comment(self):
        buf = BytesIO(u"""# -*- coding: utf-8 -*-
# NOTE: hello
msg = _('Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Bonjour à tous', messages[0][2])
        self.assertEqual([u'NOTE: hello'], messages[0][3])

    def test_utf8_message_with_utf8_bom(self):
        buf = BytesIO(codecs.BOM_UTF8 + u"""
# NOTE: hello
msg = _('Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Bonjour à tous', messages[0][2])
        self.assertEqual([u'NOTE: hello'], messages[0][3])

    def test_utf8_raw_strings_match_unicode_strings(self):
        buf = BytesIO(codecs.BOM_UTF8 + u"""
msg = _('Bonjour à tous')
msgu = _(u'Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Bonjour à tous', messages[0][2])
        self.assertEqual(messages[0][2], messages[1][2])

    def test_extract_strip_comment_tags(self):
        buf = BytesIO(b"""\
#: This is a comment with a very simple
#: prefix specified
_('Servus')

# NOTE: This is a multiline comment with
# a prefix too
_('Babatschi')""")
        messages = list(extract.extract('python', buf, comment_tags=['NOTE:', ':'],
                                        strip_comment_tags=True))
        self.assertEqual(u'Servus', messages[0][1])
        self.assertEqual([u'This is a comment with a very simple',
                          u'prefix specified'], messages[0][2])
        self.assertEqual(u'Babatschi', messages[1][1])
        self.assertEqual([u'This is a multiline comment with',
                          u'a prefix too'], messages[1][2])


class ExtractJavaScriptTestCase(unittest.TestCase):

    def test_simple_extract(self):
        buf = BytesIO(b"""\
msg1 = _('simple')
msg2 = gettext('simple')
msg3 = ngettext('s', 'p', 42)
        """)
        messages = \
            list(extract.extract('javascript', buf, extract.DEFAULT_KEYWORDS,
                                 [], {}))

        self.assertEqual([(1, 'simple', [], None),
                          (2, 'simple', [], None),
                          (3, ('s', 'p'), [], None)], messages)

    def test_various_calls(self):
        buf = BytesIO(b"""\
msg1 = _(i18n_arg.replace(/"/, '"'))
msg2 = ungettext(i18n_arg.replace(/"/, '"'), multi_arg.replace(/"/, '"'), 2)
msg3 = ungettext("Babel", multi_arg.replace(/"/, '"'), 2)
msg4 = ungettext(i18n_arg.replace(/"/, '"'), "Babels", 2)
msg5 = ungettext('bunny', 'bunnies', parseInt(Math.random() * 2 + 1))
msg6 = ungettext(arg0, 'bunnies', rparseInt(Math.random() * 2 + 1))
msg7 = _(hello.there)
msg8 = gettext('Rabbit')
msg9 = dgettext('wiki', model.addPage())
msg10 = dngettext(domain, 'Page', 'Pages', 3)
""")
        messages = \
            list(extract.extract('javascript', buf, extract.DEFAULT_KEYWORDS, [],
                                 {}))
        self.assertEqual([(5, (u'bunny', u'bunnies'), [], None),
                          (8, u'Rabbit', [], None),
                          (10, (u'Page', u'Pages'), [], None)], messages)

    def test_message_with_line_comment(self):
        buf = BytesIO(u"""\
// NOTE: hello
msg = _('Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_javascript(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Bonjour à tous', messages[0][2])
        self.assertEqual([u'NOTE: hello'], messages[0][3])

    def test_message_with_multiline_comment(self):
        buf = BytesIO(u"""\
/* NOTE: hello
   and bonjour
     and servus */
msg = _('Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_javascript(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Bonjour à tous', messages[0][2])
        self.assertEqual([u'NOTE: hello', 'and bonjour', '  and servus'], messages[0][3])

    def test_ignore_function_definitions(self):
        buf = BytesIO(b"""\
function gettext(value) {
    return translations[language][value] || value;
}""")

        messages = list(extract.extract_javascript(buf, ('gettext',), [], {}))
        self.assertEqual(messages, [])

    def test_misplaced_comments(self):
        buf = BytesIO(b"""\
/* NOTE: this won't show up */
foo()

/* NOTE: this will */
msg = _('Something')

// NOTE: this will show up
// too.
msg = _('Something else')

// NOTE: but this won't
bar()

_('no comment here')
""")
        messages = list(extract.extract_javascript(buf, ('_',), ['NOTE:'], {}))
        self.assertEqual(u'Something', messages[0][2])
        self.assertEqual([u'NOTE: this will'], messages[0][3])
        self.assertEqual(u'Something else', messages[1][2])
        self.assertEqual([u'NOTE: this will show up', 'too.'], messages[1][3])
        self.assertEqual(u'no comment here', messages[2][2])
        self.assertEqual([], messages[2][3])


class ExtractTestCase(unittest.TestCase):

    def test_invalid_filter(self):
        buf = BytesIO(b"""\
msg1 = _(i18n_arg.replace(r'\"', '"'))
msg2 = ungettext(i18n_arg.replace(r'\"', '"'), multi_arg.replace(r'\"', '"'), 2)
msg3 = ungettext("Babel", multi_arg.replace(r'\"', '"'), 2)
msg4 = ungettext(i18n_arg.replace(r'\"', '"'), "Babels", 2)
msg5 = ungettext('bunny', 'bunnies', random.randint(1, 2))
msg6 = ungettext(arg0, 'bunnies', random.randint(1, 2))
msg7 = _(hello.there)
msg8 = gettext('Rabbit')
msg9 = dgettext('wiki', model.addPage())
msg10 = dngettext(domain, 'Page', 'Pages', 3)
""")
        messages = \
            list(extract.extract('python', buf, extract.DEFAULT_KEYWORDS, [],
                                 {}))
        self.assertEqual([(5, (u'bunny', u'bunnies'), [], None),
                          (8, u'Rabbit', [], None),
                          (10, (u'Page', u'Pages'), [], None)], messages)

    def test_invalid_extract_method(self):
        buf = BytesIO(b'')
        self.assertRaises(ValueError, list, extract.extract('spam', buf))

    def test_different_signatures(self):
        buf = BytesIO(b"""
foo = _('foo', 'bar')
n = ngettext('hello', 'there', n=3)
n = ngettext(n=3, 'hello', 'there')
n = ngettext(n=3, *messages)
n = ngettext()
n = ngettext('foo')
""")
        messages = \
            list(extract.extract('python', buf, extract.DEFAULT_KEYWORDS, [],
                                 {}))
        self.assertEqual(len(messages), 2)
        self.assertEqual(u'foo', messages[0][1])
        self.assertEqual((u'hello', u'there'), messages[1][1])

    def test_empty_string_msgid(self):
        buf = BytesIO(b"""\
msg = _('')
""")
        stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            messages = \
                list(extract.extract('python', buf, extract.DEFAULT_KEYWORDS,
                                     [], {}))
            self.assertEqual([], messages)
            assert 'warning: Empty msgid.' in sys.stderr.getvalue()
        finally:
            sys.stderr = stderr

    def test_warn_if_empty_string_msgid_found_in_context_aware_extraction_method(self):
        buf = BytesIO(b"\nmsg = pgettext('ctxt', '')\n")
        stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            messages = extract.extract('python', buf)
            self.assertEqual([], list(messages))
            assert 'warning: Empty msgid.' in sys.stderr.getvalue()
        finally:
            sys.stderr = stderr

########NEW FILE########
__FILENAME__ = test_frontend
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

from datetime import datetime
from distutils.dist import Distribution
from distutils.errors import DistutilsOptionError
from distutils.log import _global_log
import logging
import os
import shutil
import sys
import time
import unittest

from babel import __version__ as VERSION
from babel.dates import format_datetime
from babel.messages import frontend
from babel.util import LOCALTZ
from babel.messages.pofile import read_po
from babel._compat import StringIO


this_dir = os.path.abspath(os.path.dirname(__file__))

class CompileCatalogTestCase(unittest.TestCase):

    def setUp(self):
        self.olddir = os.getcwd()
        self.datadir = os.path.join(this_dir, 'data')
        os.chdir(self.datadir)
        _global_log.threshold = 5 # shut up distutils logging

        self.dist = Distribution(dict(
            name='TestProject',
            version='0.1',
            packages=['project']
        ))
        self.cmd = frontend.compile_catalog(self.dist)
        self.cmd.initialize_options()

    def tearDown(self):
        os.chdir(self.olddir)

    def test_no_directory_or_output_file_specified(self):
        self.cmd.locale = 'en_US'
        self.cmd.input_file = 'dummy'
        self.assertRaises(DistutilsOptionError, self.cmd.finalize_options)

    def test_no_directory_or_input_file_specified(self):
        self.cmd.locale = 'en_US'
        self.cmd.output_file = 'dummy'
        self.assertRaises(DistutilsOptionError, self.cmd.finalize_options)


class ExtractMessagesTestCase(unittest.TestCase):

    def setUp(self):
        self.olddir = os.getcwd()
        self.datadir = os.path.join(this_dir, 'data')
        os.chdir(self.datadir)
        _global_log.threshold = 5 # shut up distutils logging

        self.dist = Distribution(dict(
            name='TestProject',
            version='0.1',
            packages=['project']
        ))
        self.cmd = frontend.extract_messages(self.dist)
        self.cmd.initialize_options()

    def tearDown(self):
        pot_file = self._pot_file()
        if os.path.isfile(pot_file):
            os.unlink(pot_file)

        os.chdir(self.olddir)

    def _i18n_dir(self):
        return os.path.join(self.datadir, 'project', 'i18n')

    def _pot_file(self):
        return os.path.join(self._i18n_dir(), 'temp.pot')

    def assert_pot_file_exists(self):
        assert os.path.isfile(self._pot_file())

    def test_neither_default_nor_custom_keywords(self):
        self.cmd.output_file = 'dummy'
        self.cmd.no_default_keywords = True
        self.assertRaises(DistutilsOptionError, self.cmd.finalize_options)

    def test_no_output_file_specified(self):
        self.assertRaises(DistutilsOptionError, self.cmd.finalize_options)

    def test_both_sort_output_and_sort_by_file(self):
        self.cmd.output_file = 'dummy'
        self.cmd.sort_output = True
        self.cmd.sort_by_file = True
        self.assertRaises(DistutilsOptionError, self.cmd.finalize_options)

    def test_input_dirs_is_treated_as_list(self):
        self.cmd.input_dirs = self.datadir
        self.cmd.output_file = self._pot_file()
        self.cmd.finalize_options()
        self.cmd.run()

        with open(self._pot_file(), 'U') as f:
            catalog = read_po(f)
        msg = catalog.get('bar')
        self.assertEqual(1, len(msg.locations))
        self.assertTrue('file1.py' in msg.locations[0][0])

    def test_input_dirs_handle_spaces_after_comma(self):
        self.cmd.input_dirs = 'foo,  bar'
        self.cmd.output_file = self._pot_file()
        self.cmd.finalize_options()

        self.assertEqual(['foo', 'bar'], self.cmd.input_dirs)

    def test_extraction_with_default_mapping(self):
        self.cmd.copyright_holder = 'FooBar, Inc.'
        self.cmd.msgid_bugs_address = 'bugs.address@email.tld'
        self.cmd.output_file = 'project/i18n/temp.pot'
        self.cmd.add_comments = 'TRANSLATOR:,TRANSLATORS:'

        self.cmd.finalize_options()
        self.cmd.run()

        self.assert_pot_file_exists()

        expected_content = r"""# Translations template for TestProject.
# Copyright (C) %(year)s FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: %(date)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. TRANSLATOR: This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

#: project/ignored/this_wont_normally_be_here.py:11
msgid "FooBar"
msgid_plural "FooBars"
msgstr[0] ""
msgstr[1] ""

""" % {'version': VERSION,
       'year': time.strftime('%Y'),
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(self._pot_file(), 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_extraction_with_mapping_file(self):
        self.cmd.copyright_holder = 'FooBar, Inc.'
        self.cmd.msgid_bugs_address = 'bugs.address@email.tld'
        self.cmd.mapping_file = 'mapping.cfg'
        self.cmd.output_file = 'project/i18n/temp.pot'
        self.cmd.add_comments = 'TRANSLATOR:,TRANSLATORS:'

        self.cmd.finalize_options()
        self.cmd.run()

        self.assert_pot_file_exists()

        expected_content = r"""# Translations template for TestProject.
# Copyright (C) %(year)s FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: %(date)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. TRANSLATOR: This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

""" % {'version': VERSION,
       'year': time.strftime('%Y'),
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(self._pot_file(), 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_extraction_with_mapping_dict(self):
        self.dist.message_extractors = {
            'project': [
                ('**/ignored/**.*', 'ignore',   None),
                ('**.py',           'python',   None),
            ]
        }
        self.cmd.copyright_holder = 'FooBar, Inc.'
        self.cmd.msgid_bugs_address = 'bugs.address@email.tld'
        self.cmd.output_file = 'project/i18n/temp.pot'
        self.cmd.add_comments = 'TRANSLATOR:,TRANSLATORS:'

        self.cmd.finalize_options()
        self.cmd.run()

        self.assert_pot_file_exists()

        expected_content = r"""# Translations template for TestProject.
# Copyright (C) %(year)s FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: %(date)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. TRANSLATOR: This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

""" % {'version': VERSION,
       'year': time.strftime('%Y'),
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(self._pot_file(), 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)


class InitCatalogTestCase(unittest.TestCase):

    def setUp(self):
        self.olddir = os.getcwd()
        self.datadir = os.path.join(this_dir, 'data')
        os.chdir(self.datadir)
        _global_log.threshold = 5 # shut up distutils logging

        self.dist = Distribution(dict(
            name='TestProject',
            version='0.1',
            packages=['project']
        ))
        self.cmd = frontend.init_catalog(self.dist)
        self.cmd.initialize_options()

    def tearDown(self):
        for dirname in ['en_US', 'ja_JP', 'lv_LV']:
            locale_dir = os.path.join(self._i18n_dir(), dirname)
            if os.path.isdir(locale_dir):
                shutil.rmtree(locale_dir)

        os.chdir(self.olddir)

    def  _i18n_dir(self):
        return os.path.join(self.datadir, 'project', 'i18n')

    def _po_file(self, locale):
        return os.path.join(self._i18n_dir(), locale, 'LC_MESSAGES',
                            'messages.po')

    def test_no_input_file(self):
        self.cmd.locale = 'en_US'
        self.cmd.output_file = 'dummy'
        self.assertRaises(DistutilsOptionError, self.cmd.finalize_options)

    def test_no_locale(self):
        self.cmd.input_file = 'dummy'
        self.cmd.output_file = 'dummy'
        self.assertRaises(DistutilsOptionError, self.cmd.finalize_options)

    def test_with_output_dir(self):
        self.cmd.input_file = 'project/i18n/messages.pot'
        self.cmd.locale = 'en_US'
        self.cmd.output_dir = 'project/i18n'

        self.cmd.finalize_options()
        self.cmd.run()

        po_file = self._po_file('en_US')
        assert os.path.isfile(po_file)

        expected_content = r"""# English (United States) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: en_US <LL@li.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

""" % {'version': VERSION,
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(po_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_keeps_catalog_non_fuzzy(self):
        self.cmd.input_file = 'project/i18n/messages_non_fuzzy.pot'
        self.cmd.locale = 'en_US'
        self.cmd.output_dir = 'project/i18n'

        self.cmd.finalize_options()
        self.cmd.run()

        po_file = self._po_file('en_US')
        assert os.path.isfile(po_file)

        expected_content = r"""# English (United States) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: en_US <LL@li.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

""" % {'version': VERSION,
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(po_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_correct_init_more_than_2_plurals(self):
        self.cmd.input_file = 'project/i18n/messages.pot'
        self.cmd.locale = 'lv_LV'
        self.cmd.output_dir = 'project/i18n'

        self.cmd.finalize_options()
        self.cmd.run()

        po_file = self._po_file('lv_LV')
        assert os.path.isfile(po_file)

        expected_content = r"""# Latvian (Latvia) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: lv_LV <LL@li.org>\n"
"Plural-Forms: nplurals=3; plural=(n%%10==1 && n%%100!=11 ? 0 : n != 0 ? 1 :"
" 2)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""
msgstr[2] ""

""" % {'version': VERSION,
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(po_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_correct_init_singular_plural_forms(self):
        self.cmd.input_file = 'project/i18n/messages.pot'
        self.cmd.locale = 'ja_JP'
        self.cmd.output_dir = 'project/i18n'

        self.cmd.finalize_options()
        self.cmd.run()

        po_file = self._po_file('ja_JP')
        assert os.path.isfile(po_file)

        expected_content = r"""# Japanese (Japan) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: ja_JP <LL@li.org>\n"
"Plural-Forms: nplurals=1; plural=0\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""

""" % {'version': VERSION,
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='ja_JP')}
        with open(po_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_supports_no_wrap(self):
        self.cmd.input_file = 'project/i18n/long_messages.pot'
        self.cmd.locale = 'en_US'
        self.cmd.output_dir = 'project/i18n'

        long_message = '"'+ 'xxxxx '*15 + '"'

        with open('project/i18n/messages.pot', 'rb') as f:
            pot_contents = f.read().decode('latin-1')
        pot_with_very_long_line = pot_contents.replace('"bar"', long_message)
        with open(self.cmd.input_file, 'wb') as f:
            f.write(pot_with_very_long_line.encode('latin-1'))
        self.cmd.no_wrap = True

        self.cmd.finalize_options()
        self.cmd.run()

        po_file = self._po_file('en_US')
        assert os.path.isfile(po_file)
        expected_content = r"""# English (United States) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: en_US <LL@li.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid %(long_message)s
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

""" % {'version': VERSION,
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en_US'),
       'long_message': long_message}
        with open(po_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_supports_width(self):
        self.cmd.input_file = 'project/i18n/long_messages.pot'
        self.cmd.locale = 'en_US'
        self.cmd.output_dir = 'project/i18n'

        long_message = '"'+ 'xxxxx '*15 + '"'

        with open('project/i18n/messages.pot', 'rb') as f:
            pot_contents = f.read().decode('latin-1')
        pot_with_very_long_line = pot_contents.replace('"bar"', long_message)
        with open(self.cmd.input_file, 'wb') as f:
            f.write(pot_with_very_long_line.encode('latin-1'))
        self.cmd.width = 120
        self.cmd.finalize_options()
        self.cmd.run()

        po_file = self._po_file('en_US')
        assert os.path.isfile(po_file)
        expected_content = r"""# English (United States) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: en_US <LL@li.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid %(long_message)s
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

""" % {'version': VERSION,
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en_US'),
       'long_message': long_message}
        with open(po_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)


class CommandLineInterfaceTestCase(unittest.TestCase):

    def setUp(self):
        self.datadir = os.path.join(this_dir, 'data')
        self.orig_working_dir = os.getcwd()
        self.orig_argv = sys.argv
        self.orig_stdout = sys.stdout
        self.orig_stderr = sys.stderr
        sys.argv = ['pybabel']
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        os.chdir(self.datadir)

        self._remove_log_handlers()
        self.cli = frontend.CommandLineInterface()

    def tearDown(self):
        os.chdir(self.orig_working_dir)
        sys.argv = self.orig_argv
        sys.stdout = self.orig_stdout
        sys.stderr = self.orig_stderr
        for dirname in ['lv_LV', 'ja_JP']:
            locale_dir = os.path.join(self._i18n_dir(), dirname)
            if os.path.isdir(locale_dir):
                shutil.rmtree(locale_dir)
        self._remove_log_handlers()

    def _remove_log_handlers(self):
        # Logging handlers will be reused if possible (#227). This breaks the
        # implicit assumption that our newly created StringIO for sys.stderr
        # contains the console output. Removing the old handler ensures that a
        # new handler with our new StringIO instance will be used.
        log = logging.getLogger('babel')
        for handler in log.handlers:
            log.removeHandler(handler)

    def test_usage(self):
        try:
            self.cli.run(sys.argv)
            self.fail('Expected SystemExit')
        except SystemExit as e:
            self.assertEqual(2, e.code)
            self.assertEqual("""\
usage: pybabel command [options] [args]

pybabel: error: no valid command or option passed. try the -h/--help option for more information.
""", sys.stderr.getvalue().lower())

    def _run_init_catalog(self):
        i18n_dir = os.path.join(self.datadir, 'project', 'i18n')
        pot_path = os.path.join(self.datadir, 'project', 'i18n', 'messages.pot')
        init_argv = sys.argv + ['init', '--locale', 'en_US', '-d', i18n_dir,
                                '-i', pot_path]
        self.cli.run(init_argv)

    def test_no_duplicated_output_for_multiple_runs(self):
        self._run_init_catalog()
        first_output = sys.stderr.getvalue()
        self._run_init_catalog()
        second_output = sys.stderr.getvalue()[len(first_output):]

        # in case the log message is not duplicated we should get the same
        # output as before
        self.assertEqual(first_output, second_output)

    def test_frontend_can_log_to_predefined_handler(self):
        custom_stream = StringIO()
        log = logging.getLogger('babel')
        log.addHandler(logging.StreamHandler(custom_stream))

        self._run_init_catalog()
        self.assertNotEqual(id(sys.stderr), id(custom_stream))
        self.assertEqual('', sys.stderr.getvalue())
        assert len(custom_stream.getvalue()) > 0

    def test_help(self):
        try:
            self.cli.run(sys.argv + ['--help'])
            self.fail('Expected SystemExit')
        except SystemExit as e:
            self.assertEqual(0, e.code)
            self.assertEqual("""\
usage: pybabel command [options] [args]

options:
  --version       show program's version number and exit
  -h, --help      show this help message and exit
  --list-locales  print all known locales and exit
  -v, --verbose   print as much as possible
  -q, --quiet     print as little as possible

commands:
  compile  compile message catalogs to mo files
  extract  extract messages from source files and generate a pot file
  init     create new message catalogs from a pot file
  update   update existing message catalogs from a pot file
""", sys.stdout.getvalue().lower())

    def _pot_file(self):
        return os.path.join(self._i18n_dir(), 'temp.pot')

    def assert_pot_file_exists(self):
        assert os.path.isfile(self._pot_file())

    def test_extract_with_default_mapping(self):
        pot_file = self._pot_file()
        self.cli.run(sys.argv + ['extract',
            '--copyright-holder', 'FooBar, Inc.',
            '--project', 'TestProject', '--version', '0.1',
            '--msgid-bugs-address', 'bugs.address@email.tld',
            '-c', 'TRANSLATOR', '-c', 'TRANSLATORS:',
            '-o', pot_file, 'project'])
        self.assert_pot_file_exists()
        expected_content = r"""# Translations template for TestProject.
# Copyright (C) %(year)s FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: %(date)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. TRANSLATOR: This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

#: project/ignored/this_wont_normally_be_here.py:11
msgid "FooBar"
msgid_plural "FooBars"
msgstr[0] ""
msgstr[1] ""

""" % {'version': VERSION,
       'year': time.strftime('%Y'),
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(pot_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_extract_with_mapping_file(self):
        pot_file = self._pot_file()
        self.cli.run(sys.argv + ['extract',
            '--copyright-holder', 'FooBar, Inc.',
            '--project', 'TestProject', '--version', '0.1',
            '--msgid-bugs-address', 'bugs.address@email.tld',
            '--mapping', os.path.join(self.datadir, 'mapping.cfg'),
            '-c', 'TRANSLATOR', '-c', 'TRANSLATORS:',
            '-o', pot_file, 'project'])
        self.assert_pot_file_exists()
        expected_content = r"""# Translations template for TestProject.
# Copyright (C) %(year)s FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: %(date)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. TRANSLATOR: This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

""" % {'version': VERSION,
       'year': time.strftime('%Y'),
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(pot_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_init_with_output_dir(self):
        po_file = self._po_file('en_US')
        self.cli.run(sys.argv + ['init',
            '--locale', 'en_US',
            '-d', os.path.join(self._i18n_dir()),
            '-i', os.path.join(self._i18n_dir(), 'messages.pot')])
        assert os.path.isfile(po_file)
        expected_content = r"""# English (United States) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: en_US <LL@li.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

""" % {'version': VERSION,
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(po_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def  _i18n_dir(self):
        return os.path.join(self.datadir, 'project', 'i18n')

    def test_init_singular_plural_forms(self):
        po_file = self._po_file('ja_JP')
        self.cli.run(sys.argv + ['init',
            '--locale', 'ja_JP',
            '-d', os.path.join(self._i18n_dir()),
            '-i', os.path.join(self._i18n_dir(), 'messages.pot')])
        assert os.path.isfile(po_file)
        expected_content = r"""# Japanese (Japan) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: ja_JP <LL@li.org>\n"
"Plural-Forms: nplurals=1; plural=0\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""

""" % {'version': VERSION,
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(po_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_init_more_than_2_plural_forms(self):
        po_file = self._po_file('lv_LV')
        self.cli.run(sys.argv + ['init',
            '--locale', 'lv_LV',
            '-d', self._i18n_dir(),
            '-i', os.path.join(self._i18n_dir(), 'messages.pot')])
        assert os.path.isfile(po_file)
        expected_content = r"""# Latvian (Latvia) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: %(date)s\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: lv_LV <LL@li.org>\n"
"Plural-Forms: nplurals=3; plural=(n%%10==1 && n%%100!=11 ? 0 : n != 0 ? 1 :"
" 2)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel %(version)s\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""
msgstr[2] ""

""" % {'version': VERSION,
       'date': format_datetime(datetime.now(LOCALTZ), 'yyyy-MM-dd HH:mmZ',
                               tzinfo=LOCALTZ, locale='en')}
        with open(po_file, 'U') as f:
            actual_content = f.read()
        self.assertEqual(expected_content, actual_content)

    def test_compile_catalog(self):
        po_file = self._po_file('de_DE')
        mo_file = po_file.replace('.po', '.mo')
        self.cli.run(sys.argv + ['compile',
            '--locale', 'de_DE',
            '-d', self._i18n_dir()])
        assert not os.path.isfile(mo_file), 'Expected no file at %r' % mo_file
        self.assertEqual("""\
catalog %r is marked as fuzzy, skipping
""" % (po_file), sys.stderr.getvalue())

    def test_compile_fuzzy_catalog(self):
        po_file = self._po_file('de_DE')
        mo_file = po_file.replace('.po', '.mo')
        try:
            self.cli.run(sys.argv + ['compile',
                '--locale', 'de_DE', '--use-fuzzy',
                '-d', self._i18n_dir()])
            assert os.path.isfile(mo_file)
            self.assertEqual("""\
compiling catalog %r to %r
""" % (po_file, mo_file), sys.stderr.getvalue())
        finally:
            if os.path.isfile(mo_file):
                os.unlink(mo_file)

    def _po_file(self, locale):
        return os.path.join(self._i18n_dir(), locale, 'LC_MESSAGES',
                            'messages.po')

    def test_compile_catalog_with_more_than_2_plural_forms(self):
        po_file = self._po_file('ru_RU')
        mo_file = po_file.replace('.po', '.mo')
        try:
            self.cli.run(sys.argv + ['compile',
                '--locale', 'ru_RU', '--use-fuzzy',
                '-d', self._i18n_dir()])
            assert os.path.isfile(mo_file)
            self.assertEqual("""\
compiling catalog %r to %r
""" % (po_file, mo_file), sys.stderr.getvalue())
        finally:
            if os.path.isfile(mo_file):
                os.unlink(mo_file)


def test_parse_mapping():
    buf = StringIO(
        '[extractors]\n'
        'custom = mypackage.module:myfunc\n'
        '\n'
        '# Python source files\n'
        '[python: **.py]\n'
        '\n'
        '# Genshi templates\n'
        '[genshi: **/templates/**.html]\n'
        'include_attrs =\n'
        '[genshi: **/templates/**.txt]\n'
        'template_class = genshi.template:TextTemplate\n'
        'encoding = latin-1\n'
        '\n'
        '# Some custom extractor\n'
        '[custom: **/custom/*.*]\n')

    method_map, options_map = frontend.parse_mapping(buf)
    assert len(method_map) == 4

    assert method_map[0] == ('**.py', 'python')
    assert options_map['**.py'] == {}
    assert method_map[1] == ('**/templates/**.html', 'genshi')
    assert options_map['**/templates/**.html']['include_attrs'] == ''
    assert method_map[2] == ('**/templates/**.txt', 'genshi')
    assert (options_map['**/templates/**.txt']['template_class']
            == 'genshi.template:TextTemplate')
    assert options_map['**/templates/**.txt']['encoding'] == 'latin-1'

    assert method_map[3] == ('**/custom/*.*', 'mypackage.module:myfunc')
    assert options_map['**/custom/*.*'] == {}


def test_parse_keywords():
    kw = frontend.parse_keywords(['_', 'dgettext:2',
                                  'dngettext:2,3', 'pgettext:1c,2'])
    assert kw == {
        '_': None,
        'dgettext': (2,),
        'dngettext': (2, 3),
        'pgettext': ((1, 'c'), 2),
    }

########NEW FILE########
__FILENAME__ = test_jslexer
# -*- coding: utf-8 -*-

from babel.messages import jslexer


def test_unquote():
    assert jslexer.unquote_string('""') == ''
    assert jslexer.unquote_string(r'"h\u00ebllo"') == u"hëllo"

########NEW FILE########
__FILENAME__ = test_mofile
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import os
import unittest

from babel.messages import mofile, Catalog
from babel._compat import BytesIO, text_type
from babel.support import Translations


class ReadMoTestCase(unittest.TestCase):

    def setUp(self):
        self.datadir = os.path.join(os.path.dirname(__file__), 'data')

    def test_basics(self):
        mo_path = os.path.join(self.datadir, 'project', 'i18n', 'de',
                               'LC_MESSAGES', 'messages.mo')
        mo_file = open(mo_path, 'rb')
        try:
            catalog = mofile.read_mo(mo_file)
            self.assertEqual(2, len(catalog))
            self.assertEqual('TestProject', catalog.project)
            self.assertEqual('0.1', catalog.version)
            self.assertEqual('Stange', catalog['bar'].string)
            self.assertEqual(['Fuhstange', 'Fuhstangen'],
                             catalog['foobar'].string)
        finally:
            mo_file.close()


class WriteMoTestCase(unittest.TestCase):

    def test_sorting(self):
        # Ensure the header is sorted to the first entry so that its charset
        # can be applied to all subsequent messages by GNUTranslations
        # (ensuring all messages are safely converted to unicode)
        catalog = Catalog(locale='en_US')
        catalog.add(u'', '''\
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n''')
        catalog.add(u'foo', 'Voh')
        catalog.add((u'There is', u'There are'), (u'Es gibt', u'Es gibt'))
        catalog.add(u'Fizz', '')
        catalog.add(('Fuzz', 'Fuzzes'), ('', ''))
        buf = BytesIO()
        mofile.write_mo(buf, catalog)
        buf.seek(0)
        translations = Translations(fp=buf)
        self.assertEqual(u'Voh', translations.ugettext('foo'))
        assert isinstance(translations.ugettext('foo'), text_type)
        self.assertEqual(u'Es gibt', translations.ungettext('There is', 'There are', 1))
        assert isinstance(translations.ungettext('There is', 'There are', 1), text_type)
        self.assertEqual(u'Fizz', translations.ugettext('Fizz'))
        assert isinstance(translations.ugettext('Fizz'), text_type)
        self.assertEqual(u'Fuzz', translations.ugettext('Fuzz'))
        assert isinstance(translations.ugettext('Fuzz'), text_type)
        self.assertEqual(u'Fuzzes', translations.ugettext('Fuzzes'))
        assert isinstance(translations.ugettext('Fuzzes'), text_type)

    def test_more_plural_forms(self):
        catalog2 = Catalog(locale='ru_RU')
        catalog2.add(('Fuzz', 'Fuzzes'), ('', '', ''))
        buf = BytesIO()
        mofile.write_mo(buf, catalog2)

########NEW FILE########
__FILENAME__ = test_plurals
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import doctest
import unittest

from babel.messages import plurals


def test_get_plural():
    assert plurals.get_plural(locale='en') == (2, '(n != 1)')
    assert plurals.get_plural(locale='ga') == (3, '(n==1 ? 0 : n==2 ? 1 : 2)')

    tup = plurals.get_plural("ja")
    assert tup.num_plurals == 1
    assert tup.plural_expr == '0'
    assert tup.plural_forms == 'npurals=1; plural=0'
    assert str(tup) == 'npurals=1; plural=0'

########NEW FILE########
__FILENAME__ = test_pofile
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

from datetime import datetime
import unittest

from babel.core import Locale
from babel.messages.catalog import Catalog, Message
from babel.messages import pofile
from babel.util import FixedOffsetTimezone
from babel._compat import StringIO, BytesIO


class ReadPoTestCase(unittest.TestCase):

    def test_preserve_locale(self):
        buf = StringIO(r'''msgid "foo"
msgstr "Voh"''')
        catalog = pofile.read_po(buf, locale='en_US')
        self.assertEqual(Locale('en', 'US'), catalog.locale)

    def test_preserve_domain(self):
        buf = StringIO(r'''msgid "foo"
msgstr "Voh"''')
        catalog = pofile.read_po(buf, domain='mydomain')
        self.assertEqual('mydomain', catalog.domain)

    def test_applies_specified_encoding_during_read(self):
        buf = BytesIO(u'''
msgid ""
msgstr ""
"Project-Id-Version:  3.15\\n"
"Report-Msgid-Bugs-To: Fliegender Zirkus <fliegender@zirkus.de>\\n"
"POT-Creation-Date: 2007-09-27 11:19+0700\\n"
"PO-Revision-Date: 2007-09-27 21:42-0700\\n"
"Last-Translator: John <cleese@bavaria.de>\\n"
"Language-Team: German Lang <de@babel.org>\\n"
"Plural-Forms: nplurals=2; plural=(n != 1)\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=iso-8859-1\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Generated-By: Babel 1.0dev-r313\\n"

msgid "foo"
msgstr "bär"'''.encode('iso-8859-1'))
        catalog = pofile.read_po(buf, locale='de_DE')
        self.assertEqual(u'bär', catalog.get('foo').string)

    def test_read_multiline(self):
        buf = StringIO(r'''msgid ""
"Here's some text that\n"
"includesareallylongwordthatmightbutshouldnt"
" throw us into an infinite "
"loop\n"
msgstr ""''')
        catalog = pofile.read_po(buf)
        self.assertEqual(1, len(catalog))
        message = list(catalog)[1]
        self.assertEqual("Here's some text that\nincludesareallylongwordthat"
                         "mightbutshouldnt throw us into an infinite loop\n",
                         message.id)

    def test_fuzzy_header(self):
        buf = StringIO(r'''\
# Translations template for AReallyReallyLongNameForAProject.
# Copyright (C) 2007 ORGANIZATION
# This file is distributed under the same license as the
# AReallyReallyLongNameForAProject project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
#, fuzzy
''')
        catalog = pofile.read_po(buf)
        self.assertEqual(1, len(list(catalog)))
        self.assertEqual(True, list(catalog)[0].fuzzy)

    def test_not_fuzzy_header(self):
        buf = StringIO(r'''\
# Translations template for AReallyReallyLongNameForAProject.
# Copyright (C) 2007 ORGANIZATION
# This file is distributed under the same license as the
# AReallyReallyLongNameForAProject project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
''')
        catalog = pofile.read_po(buf)
        self.assertEqual(1, len(list(catalog)))
        self.assertEqual(False, list(catalog)[0].fuzzy)

    def test_header_entry(self):
        buf = StringIO(r'''\
# SOME DESCRIPTIVE TITLE.
# Copyright (C) 2007 THE PACKAGE'S COPYRIGHT HOLDER
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version:  3.15\n"
"Report-Msgid-Bugs-To: Fliegender Zirkus <fliegender@zirkus.de>\n"
"POT-Creation-Date: 2007-09-27 11:19+0700\n"
"PO-Revision-Date: 2007-09-27 21:42-0700\n"
"Last-Translator: John <cleese@bavaria.de>\n"
"Language-Team: German Lang <de@babel.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=iso-8859-2\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel 1.0dev-r313\n"
''')
        catalog = pofile.read_po(buf)
        self.assertEqual(1, len(list(catalog)))
        self.assertEqual(u'3.15', catalog.version)
        self.assertEqual(u'Fliegender Zirkus <fliegender@zirkus.de>',
                         catalog.msgid_bugs_address)
        self.assertEqual(datetime(2007, 9, 27, 11, 19,
                                  tzinfo=FixedOffsetTimezone(7 * 60)),
                         catalog.creation_date)
        self.assertEqual(u'John <cleese@bavaria.de>', catalog.last_translator)
        self.assertEqual(u'German Lang <de@babel.org>', catalog.language_team)
        self.assertEqual(u'iso-8859-2', catalog.charset)
        self.assertEqual(True, list(catalog)[0].fuzzy)

    def test_obsolete_message(self):
        buf = StringIO(r'''# This is an obsolete message
#~ msgid "foo"
#~ msgstr "Voh"

# This message is not obsolete
#: main.py:1
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf)
        self.assertEqual(1, len(catalog))
        self.assertEqual(1, len(catalog.obsolete))
        message = catalog.obsolete[u'foo']
        self.assertEqual(u'foo', message.id)
        self.assertEqual(u'Voh', message.string)
        self.assertEqual(['This is an obsolete message'], message.user_comments)

    def test_obsolete_message_ignored(self):
        buf = StringIO(r'''# This is an obsolete message
#~ msgid "foo"
#~ msgstr "Voh"

# This message is not obsolete
#: main.py:1
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf, ignore_obsolete=True)
        self.assertEqual(1, len(catalog))
        self.assertEqual(0, len(catalog.obsolete))

    def test_with_context(self):
        buf = BytesIO(b'''# Some string in the menu
#: main.py:1
msgctxt "Menu"
msgid "foo"
msgstr "Voh"

# Another string in the menu
#: main.py:2
msgctxt "Menu"
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf, ignore_obsolete=True)
        self.assertEqual(2, len(catalog))
        message = catalog.get('foo', context='Menu')
        self.assertEqual('Menu', message.context)
        message = catalog.get('bar', context='Menu')
        self.assertEqual('Menu', message.context)

        # And verify it pass through write_po
        out_buf = BytesIO()
        pofile.write_po(out_buf, catalog, omit_header=True)
        assert out_buf.getvalue().strip() == buf.getvalue().strip(), \
                                                            out_buf.getvalue()

    def test_with_context_two(self):
        buf = BytesIO(b'''msgctxt "Menu"
msgid "foo"
msgstr "Voh"

msgctxt "Mannu"
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf, ignore_obsolete=True)
        self.assertEqual(2, len(catalog))
        message = catalog.get('foo', context='Menu')
        self.assertEqual('Menu', message.context)
        message = catalog.get('bar', context='Mannu')
        self.assertEqual('Mannu', message.context)

        # And verify it pass through write_po
        out_buf = BytesIO()
        pofile.write_po(out_buf, catalog, omit_header=True)
        assert out_buf.getvalue().strip() == buf.getvalue().strip(), out_buf.getvalue()

    def test_single_plural_form(self):
        buf = StringIO(r'''msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"''')
        catalog = pofile.read_po(buf, locale='ja_JP')
        self.assertEqual(1, len(catalog))
        self.assertEqual(1, catalog.num_plurals)
        message = catalog['foo']
        self.assertEqual(1, len(message.string))

    def test_singular_plural_form(self):
        buf = StringIO(r'''msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Vohs"''')
        catalog = pofile.read_po(buf, locale='nl_NL')
        self.assertEqual(1, len(catalog))
        self.assertEqual(2, catalog.num_plurals)
        message = catalog['foo']
        self.assertEqual(2, len(message.string))

    def test_more_than_two_plural_forms(self):
        buf = StringIO(r'''msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Vohs"
msgstr[2] "Vohss"''')
        catalog = pofile.read_po(buf, locale='lv_LV')
        self.assertEqual(1, len(catalog))
        self.assertEqual(3, catalog.num_plurals)
        message = catalog['foo']
        self.assertEqual(3, len(message.string))
        self.assertEqual(u'Vohss', message.string[2])

    def test_plural_with_square_brackets(self):
        buf = StringIO(r'''msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh [text]"
msgstr[1] "Vohs [text]"''')
        catalog = pofile.read_po(buf, locale='nb_NO')
        self.assertEqual(1, len(catalog))
        self.assertEqual(2, catalog.num_plurals)
        message = catalog['foo']
        self.assertEqual(2, len(message.string))


class WritePoTestCase(unittest.TestCase):

    def test_join_locations(self):
        catalog = Catalog()
        catalog.add(u'foo', locations=[('main.py', 1)])
        catalog.add(u'foo', locations=[('utils.py', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        self.assertEqual(b'''#: main.py:1 utils.py:3
msgid "foo"
msgstr ""''', buf.getvalue().strip())

    def test_write_po_file_with_specified_charset(self):
        catalog = Catalog(charset='iso-8859-1')
        catalog.add('foo', u'äöü', locations=[('main.py', 1)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=False)
        po_file = buf.getvalue().strip()
        assert b'"Content-Type: text/plain; charset=iso-8859-1\\n"' in po_file
        assert u'msgstr "äöü"'.encode('iso-8859-1') in po_file

    def test_duplicate_comments(self):
        catalog = Catalog()
        catalog.add(u'foo', auto_comments=['A comment'])
        catalog.add(u'foo', auto_comments=['A comment'])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        self.assertEqual(b'''#. A comment
msgid "foo"
msgstr ""''', buf.getvalue().strip())

    def test_wrap_long_lines(self):
        text = """Here's some text where
white space and line breaks matter, and should

not be removed

"""
        catalog = Catalog()
        catalog.add(text, locations=[('main.py', 1)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, no_location=True, omit_header=True,
                         width=42)
        self.assertEqual(b'''msgid ""
"Here's some text where\\n"
"white space and line breaks matter, and"
" should\\n"
"\\n"
"not be removed\\n"
"\\n"
msgstr ""''', buf.getvalue().strip())

    def test_wrap_long_lines_with_long_word(self):
        text = """Here's some text that
includesareallylongwordthatmightbutshouldnt throw us into an infinite loop
"""
        catalog = Catalog()
        catalog.add(text, locations=[('main.py', 1)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, no_location=True, omit_header=True,
                         width=32)
        self.assertEqual(b'''msgid ""
"Here's some text that\\n"
"includesareallylongwordthatmightbutshouldnt"
" throw us into an infinite "
"loop\\n"
msgstr ""''', buf.getvalue().strip())

    def test_wrap_long_lines_in_header(self):
        """
        Verify that long lines in the header comment are wrapped correctly.
        """
        catalog = Catalog(project='AReallyReallyLongNameForAProject',
                          revision_date=datetime(2007, 4, 1))
        buf = BytesIO()
        pofile.write_po(buf, catalog)
        self.assertEqual(b'''\
# Translations template for AReallyReallyLongNameForAProject.
# Copyright (C) 2007 ORGANIZATION
# This file is distributed under the same license as the
# AReallyReallyLongNameForAProject project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
#, fuzzy''', b'\n'.join(buf.getvalue().splitlines()[:7]))

    def test_wrap_locations_with_hyphens(self):
        catalog = Catalog()
        catalog.add(u'foo', locations=[
            ('doupy/templates/base/navmenu.inc.html.py', 60)
        ])
        catalog.add(u'foo', locations=[
            ('doupy/templates/job-offers/helpers.html', 22)
        ])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        self.assertEqual(b'''#: doupy/templates/base/navmenu.inc.html.py:60
#: doupy/templates/job-offers/helpers.html:22
msgid "foo"
msgstr ""''', buf.getvalue().strip())

    def test_no_wrap_and_width_behaviour_on_comments(self):
        catalog = Catalog()
        catalog.add("Pretty dam long message id, which must really be big "
                    "to test this wrap behaviour, if not it won't work.",
                    locations=[("fake.py", n) for n in range(1, 30)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, width=None, omit_header=True)
        self.assertEqual(b"""\
#: fake.py:1 fake.py:2 fake.py:3 fake.py:4 fake.py:5 fake.py:6 fake.py:7
#: fake.py:8 fake.py:9 fake.py:10 fake.py:11 fake.py:12 fake.py:13 fake.py:14
#: fake.py:15 fake.py:16 fake.py:17 fake.py:18 fake.py:19 fake.py:20 fake.py:21
#: fake.py:22 fake.py:23 fake.py:24 fake.py:25 fake.py:26 fake.py:27 fake.py:28
#: fake.py:29
msgid "pretty dam long message id, which must really be big to test this wrap behaviour, if not it won't work."
msgstr ""

""", buf.getvalue().lower())
        buf = BytesIO()
        pofile.write_po(buf, catalog, width=100, omit_header=True)
        self.assertEqual(b"""\
#: fake.py:1 fake.py:2 fake.py:3 fake.py:4 fake.py:5 fake.py:6 fake.py:7 fake.py:8 fake.py:9 fake.py:10
#: fake.py:11 fake.py:12 fake.py:13 fake.py:14 fake.py:15 fake.py:16 fake.py:17 fake.py:18 fake.py:19
#: fake.py:20 fake.py:21 fake.py:22 fake.py:23 fake.py:24 fake.py:25 fake.py:26 fake.py:27 fake.py:28
#: fake.py:29
msgid ""
"pretty dam long message id, which must really be big to test this wrap behaviour, if not it won't"
" work."
msgstr ""

""", buf.getvalue().lower())

    def test_pot_with_translator_comments(self):
        catalog = Catalog()
        catalog.add(u'foo', locations=[('main.py', 1)],
                    auto_comments=['Comment About `foo`'])
        catalog.add(u'bar', locations=[('utils.py', 3)],
                    user_comments=['Comment About `bar` with',
                                   'multiple lines.'])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        self.assertEqual(b'''#. Comment About `foo`
#: main.py:1
msgid "foo"
msgstr ""

# Comment About `bar` with
# multiple lines.
#: utils.py:3
msgid "bar"
msgstr ""''', buf.getvalue().strip())

    def test_po_with_obsolete_message(self):
        catalog = Catalog()
        catalog.add(u'foo', u'Voh', locations=[('main.py', 1)])
        catalog.obsolete['bar'] = Message(u'bar', u'Bahr',
                                          locations=[('utils.py', 3)],
                                          user_comments=['User comment'])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        self.assertEqual(b'''#: main.py:1
msgid "foo"
msgstr "Voh"

# User comment
#~ msgid "bar"
#~ msgstr "Bahr"''', buf.getvalue().strip())

    def test_po_with_multiline_obsolete_message(self):
        catalog = Catalog()
        catalog.add(u'foo', u'Voh', locations=[('main.py', 1)])
        msgid = r"""Here's a message that covers
multiple lines, and should still be handled
correctly.
"""
        msgstr = r"""Here's a message that covers
multiple lines, and should still be handled
correctly.
"""
        catalog.obsolete[msgid] = Message(msgid, msgstr,
                                          locations=[('utils.py', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        self.assertEqual(b'''#: main.py:1
msgid "foo"
msgstr "Voh"

#~ msgid ""
#~ "Here's a message that covers\\n"
#~ "multiple lines, and should still be handled\\n"
#~ "correctly.\\n"
#~ msgstr ""
#~ "Here's a message that covers\\n"
#~ "multiple lines, and should still be handled\\n"
#~ "correctly.\\n"''', buf.getvalue().strip())

    def test_po_with_obsolete_message_ignored(self):
        catalog = Catalog()
        catalog.add(u'foo', u'Voh', locations=[('main.py', 1)])
        catalog.obsolete['bar'] = Message(u'bar', u'Bahr',
                                          locations=[('utils.py', 3)],
                                          user_comments=['User comment'])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, ignore_obsolete=True)
        self.assertEqual(b'''#: main.py:1
msgid "foo"
msgstr "Voh"''', buf.getvalue().strip())

    def test_po_with_previous_msgid(self):
        catalog = Catalog()
        catalog.add(u'foo', u'Voh', locations=[('main.py', 1)],
                    previous_id=u'fo')
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_previous=True)
        self.assertEqual(b'''#: main.py:1
#| msgid "fo"
msgid "foo"
msgstr "Voh"''', buf.getvalue().strip())

    def test_po_with_previous_msgid_plural(self):
        catalog = Catalog()
        catalog.add((u'foo', u'foos'), (u'Voh', u'Voeh'),
                    locations=[('main.py', 1)], previous_id=(u'fo', u'fos'))
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_previous=True)
        self.assertEqual(b'''#: main.py:1
#| msgid "fo"
#| msgid_plural "fos"
msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Voeh"''', buf.getvalue().strip())

    def test_sorted_po(self):
        catalog = Catalog()
        catalog.add(u'bar', locations=[('utils.py', 3)],
                    user_comments=['Comment About `bar` with',
                                   'multiple lines.'])
        catalog.add((u'foo', u'foos'), (u'Voh', u'Voeh'),
                    locations=[('main.py', 1)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, sort_output=True)
        value = buf.getvalue().strip()
        assert b'''\
# Comment About `bar` with
# multiple lines.
#: utils.py:3
msgid "bar"
msgstr ""

#: main.py:1
msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Voeh"''' in value
        assert value.find(b'msgid ""') < value.find(b'msgid "bar"') < value.find(b'msgid "foo"')

    def test_silent_location_fallback(self):
        buf = BytesIO(b'''\
#: broken_file.py
msgid "missing line number"
msgstr ""

#: broken_file.py:broken_line_number
msgid "broken line number"
msgstr ""''')
        catalog = pofile.read_po(buf)
        self.assertEqual(catalog['missing line number'].locations, [])
        self.assertEqual(catalog['broken line number'].locations, [])


class PofileFunctionsTestCase(unittest.TestCase):

    def test_unescape(self):
        escaped = u'"Say:\\n  \\"hello, world!\\"\\n"'
        unescaped = u'Say:\n  "hello, world!"\n'
        self.assertNotEqual(unescaped, escaped)
        self.assertEqual(unescaped, pofile.unescape(escaped))

    def test_unescape_of_quoted_newline(self):
        # regression test for #198
        self.assertEqual(r'\n', pofile.unescape(r'"\\n"'))

    def test_denormalize_on_msgstr_without_empty_first_line(self):
        # handle irregular multi-line msgstr (no "" as first line)
        # gracefully (#171)
        msgstr = '"multi-line\\n"\n" translation"'
        expected_denormalized = u'multi-line\n translation'

        self.assertEqual(expected_denormalized, pofile.denormalize(msgstr))
        self.assertEqual(expected_denormalized,
                         pofile.denormalize('""\n' + msgstr))

########NEW FILE########
__FILENAME__ = test_core
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import doctest
import unittest
import pytest

from babel import core, Locale
from babel.core import default_locale, Locale


def test_locale_provides_access_to_cldr_locale_data():
    locale = Locale('en', 'US')
    assert u'English (United States)' == locale.display_name
    assert u'.' == locale.number_symbols['decimal']

def test_locale_repr():
    assert ("Locale('de', territory='DE')" == repr(Locale('de', 'DE')))
    assert ("Locale('zh', territory='CN', script='Hans')" ==
            repr(Locale('zh', 'CN', script='Hans')))

def test_locale_comparison():
    en_US = Locale('en', 'US')
    assert en_US == en_US
    assert None != en_US

    bad_en_US = Locale('en_US')
    assert en_US != bad_en_US

def test_can_return_default_locale(os_environ):
    os_environ['LC_MESSAGES'] = 'fr_FR.UTF-8'
    assert Locale('fr', 'FR') == Locale.default('LC_MESSAGES')


def test_ignore_invalid_locales_in_lc_ctype(os_environ):
    # This is a regression test specifically for a bad LC_CTYPE setting on
    # MacOS X 10.6 (#200)
    os_environ['LC_CTYPE'] = 'UTF-8'
    # must not throw an exception
    default_locale('LC_CTYPE')


def test_get_global():
    assert core.get_global('zone_aliases')['UTC'] == 'Etc/GMT'
    assert core.get_global('zone_territories')['Europe/Berlin'] == 'DE'


class TestLocaleClass:

    def test_repr(self):
        assert repr(Locale('en', 'US')) == "Locale('en', territory='US')"

    def test_attributes(self):
        locale = Locale('en', 'US')
        assert locale.language == 'en'
        assert locale.territory == 'US'

    def test_default(self, os_environ):
        for name in ['LANGUAGE', 'LC_ALL', 'LC_CTYPE', 'LC_MESSAGES']:
            os_environ[name] = ''
        os_environ['LANG'] = 'fr_FR.UTF-8'
        default = Locale.default('LC_MESSAGES')
        assert (default.language, default.territory) == ('fr', 'FR')

    def test_negotiate(self):
        de_DE = Locale.negotiate(['de_DE', 'en_US'], ['de_DE', 'de_AT'])
        assert (de_DE.language, de_DE.territory) == ('de', 'DE')
        de = Locale.negotiate(['de_DE', 'en_US'], ['en', 'de'])
        assert (de.language, de.territory) == ('de', None)
        nothing = Locale.negotiate(['de_DE', 'de'], ['en_US'])
        assert nothing is None

    def test_negotiate_custom_separator(self):
        de_DE = Locale.negotiate(['de-DE', 'de'], ['en-us', 'de-de'], sep='-')
        assert (de_DE.language, de_DE.territory) == ('de', 'DE')

    def test_parse(self):
        l = Locale.parse('de-DE', sep='-')
        assert l.display_name == 'Deutsch (Deutschland)'

        de_DE = Locale.parse(l)
        assert (de_DE.language, de_DE.territory) == ('de', 'DE')

    def test_parse_likely_subtags(self):
        l = Locale.parse('zh-TW', sep='-')
        assert l.language == 'zh'
        assert l.territory == 'TW'
        assert l.script == 'Hant'

        l = Locale.parse('zh_CN')
        assert l.language == 'zh'
        assert l.territory == 'CN'
        assert l.script == 'Hans'

        l = Locale.parse('zh_SG')
        assert l.language == 'zh'
        assert l.territory == 'SG'
        assert l.script == 'Hans'

        l = Locale.parse('und_AT')
        assert l.language == 'de'
        assert l.territory == 'AT'

        l = Locale.parse('und_UK')
        assert l.language == 'en'
        assert l.territory == 'GB'
        assert l.script is None

    def test_get_display_name(self):
        zh_CN = Locale('zh', 'CN', script='Hans')
        assert zh_CN.get_display_name('en') == 'Chinese (Simplified, China)'

    def test_display_name_property(self):
        assert Locale('en').display_name == 'English'
        assert Locale('en', 'US').display_name == 'English (United States)'
        assert Locale('sv').display_name == 'svenska'

    def test_english_name_property(self):
        assert Locale('de').english_name == 'German'
        assert Locale('de', 'DE').english_name == 'German (Germany)'

    def test_languages_property(self):
        assert Locale('de', 'DE').languages['ja'] == 'Japanisch'

    def test_scripts_property(self):
        assert Locale('en', 'US').scripts['Hira'] == 'Hiragana'

    def test_territories_property(self):
        assert Locale('es', 'CO').territories['DE'] == 'Alemania'

    def test_variants_property(self):
        assert (Locale('de', 'DE').variants['1901'] ==
                'Alte deutsche Rechtschreibung')

    def test_currencies_property(self):
        assert Locale('en').currencies['COP'] == 'Colombian Peso'
        assert Locale('de', 'DE').currencies['COP'] == 'Kolumbianischer Peso'

    def test_currency_symbols_property(self):
        assert Locale('en', 'US').currency_symbols['USD'] == '$'
        assert Locale('es', 'CO').currency_symbols['USD'] == 'US$'

    def test_number_symbols_property(self):
        assert Locale('fr', 'FR').number_symbols['decimal'] == ','

    def test_decimal_formats(self):
        assert Locale('en', 'US').decimal_formats[None].pattern == '#,##0.###'

    def test_currency_formats_property(self):
        assert (Locale('en', 'US').currency_formats[None].pattern ==
                u'\xa4#,##0.00')

    def test_percent_formats_property(self):
        assert Locale('en', 'US').percent_formats[None].pattern == '#,##0%'

    def test_scientific_formats_property(self):
        assert Locale('en', 'US').scientific_formats[None].pattern == '#E0'

    def test_periods_property(self):
        assert Locale('en', 'US').periods['am'] == 'AM'

    def test_days_property(self):
        assert Locale('de', 'DE').days['format']['wide'][3] == 'Donnerstag'

    def test_months_property(self):
        assert Locale('de', 'DE').months['format']['wide'][10] == 'Oktober'

    def test_quarters_property(self):
        assert Locale('de', 'DE').quarters['format']['wide'][1] == '1. Quartal'

    def test_eras_property(self):
        assert Locale('en', 'US').eras['wide'][1] == 'Anno Domini'
        assert Locale('en', 'US').eras['abbreviated'][0] == 'BC'

    def test_time_zones_property(self):
        time_zones = Locale('en', 'US').time_zones
        assert (time_zones['Europe/London']['long']['daylight'] ==
                'British Summer Time')
        assert time_zones['America/St_Johns']['city'] == u'St. John\u2019s'

    def test_meta_zones_property(self):
        meta_zones = Locale('en', 'US').meta_zones
        assert (meta_zones['Europe_Central']['long']['daylight'] ==
                'Central European Summer Time')

    def test_zone_formats_property(self):
        assert Locale('en', 'US').zone_formats['fallback'] == '%(1)s (%(0)s)'
        assert Locale('pt', 'BR').zone_formats['region'] == u'Hor\xe1rio %s'

    def test_first_week_day_property(self):
        assert Locale('de', 'DE').first_week_day == 0
        assert Locale('en', 'US').first_week_day == 6

    def test_weekend_start_property(self):
        assert Locale('de', 'DE').weekend_start == 5

    def test_weekend_end_property(self):
        assert Locale('de', 'DE').weekend_end == 6

    def test_min_week_days_property(self):
        assert Locale('de', 'DE').min_week_days == 4

    def test_date_formats_property(self):
        assert Locale('en', 'US').date_formats['short'].pattern == 'M/d/yy'
        assert Locale('fr', 'FR').date_formats['long'].pattern == 'd MMMM y'

    def test_time_formats_property(self):
        assert Locale('en', 'US').time_formats['short'].pattern == 'h:mm a'
        assert Locale('fr', 'FR').time_formats['long'].pattern == 'HH:mm:ss z'

    def test_datetime_formats_property(self):
        assert Locale('en').datetime_formats['full'] == u"{1} 'at' {0}"
        assert Locale('th').datetime_formats['medium'] == u'{1}, {0}'

    def test_plural_form_property(self):
        assert Locale('en').plural_form(1) == 'one'
        assert Locale('en').plural_form(0) == 'other'
        assert Locale('fr').plural_form(0) == 'one'
        assert Locale('ru').plural_form(100) == 'many'


def test_default_locale(os_environ):
    for name in ['LANGUAGE', 'LC_ALL', 'LC_CTYPE', 'LC_MESSAGES']:
        os_environ[name] = ''
    os_environ['LANG'] = 'fr_FR.UTF-8'
    assert default_locale('LC_MESSAGES') == 'fr_FR'

    os_environ['LC_MESSAGES'] = 'POSIX'
    assert default_locale('LC_MESSAGES') == 'en_US_POSIX'

    for value in ['C', 'C.UTF-8', 'POSIX']:
        os_environ['LANGUAGE'] = value
        assert default_locale() == 'en_US_POSIX'


def test_negotiate_locale():
    assert (core.negotiate_locale(['de_DE', 'en_US'], ['de_DE', 'de_AT']) ==
            'de_DE')
    assert core.negotiate_locale(['de_DE', 'en_US'], ['en', 'de']) == 'de'
    assert (core.negotiate_locale(['de_DE', 'en_US'], ['de_de', 'de_at']) ==
            'de_DE')
    assert (core.negotiate_locale(['de_DE', 'en_US'], ['de_de', 'de_at']) ==
            'de_DE')
    assert (core.negotiate_locale(['ja', 'en_US'], ['ja_JP', 'en_US']) ==
            'ja_JP')
    assert core.negotiate_locale(['no', 'sv'], ['nb_NO', 'sv_SE']) == 'nb_NO'

def test_parse_locale():
    assert core.parse_locale('zh_CN') == ('zh', 'CN', None, None)
    assert core.parse_locale('zh_Hans_CN') == ('zh', 'CN', 'Hans', None)
    assert core.parse_locale('zh-CN', sep='-') == ('zh', 'CN', None, None)

    with pytest.raises(ValueError) as excinfo:
        core.parse_locale('not_a_LOCALE_String')
    assert (excinfo.value.args[0] ==
            "'not_a_LOCALE_String' is not a valid locale identifier")

    assert core.parse_locale('it_IT@euro') == ('it', 'IT', None, None)
    assert core.parse_locale('en_US.UTF-8') == ('en', 'US', None, None)
    assert (core.parse_locale('de_DE.iso885915@euro') ==
            ('de', 'DE', None, None))

########NEW FILE########
__FILENAME__ = test_dates
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import calendar
from datetime import date, datetime, time, timedelta
import types
import unittest

from pytz import timezone

from babel import dates, Locale
from babel.util import FixedOffsetTimezone


class DateTimeFormatTestCase(unittest.TestCase):

    def test_quarter_format(self):
        d = date(2006, 6, 8)
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('2', fmt['Q'])
        self.assertEqual('2nd quarter', fmt['QQQQ'])
        d = date(2006, 12, 31)
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('Q4', fmt['QQQ'])

    def test_month_context(self):
        d = date(2006, 2, 8)
        fmt = dates.DateTimeFormat(d, locale='cs_CZ')
        self.assertEqual(u'2', fmt['MMMMM']) # narrow format
        fmt = dates.DateTimeFormat(d, locale='cs_CZ')
        self.assertEqual(u'ú', fmt['LLLLL']) # narrow standalone

    def test_abbreviated_month_alias(self):
        d = date(2006, 3, 8)
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual(u'Mär', fmt['LLL'])

    def test_week_of_year_first(self):
        d = date(2006, 1, 8)
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual('1', fmt['w'])
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('02', fmt['ww'])

    def test_week_of_year_first_with_year(self):
        d = date(2006, 1, 1)
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual('52', fmt['w'])
        self.assertEqual('2005', fmt['YYYY'])

    def test_week_of_year_last(self):
        d = date(2006, 12, 26)
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual('52', fmt['w'])
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('52', fmt['w'])

    def test_week_of_year_last_us_extra_week(self):
        d = date(2005, 12, 26)
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual('52', fmt['w'])
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('53', fmt['w'])

    def test_week_of_month_first(self):
        d = date(2006, 1, 8)
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual('1', fmt['W'])
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('2', fmt['W'])

    def test_week_of_month_last(self):
        d = date(2006, 1, 29)
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual('4', fmt['W'])
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('5', fmt['W'])

    def test_day_of_year(self):
        d = date(2007, 4, 1)
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('91', fmt['D'])

    def test_day_of_year_works_with_datetime(self):
        d = datetime(2007, 4, 1)
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('91', fmt['D'])

    def test_day_of_year_first(self):
        d = date(2007, 1, 1)
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('001', fmt['DDD'])

    def test_day_of_year_last(self):
        d = date(2007, 12, 31)
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('365', fmt['DDD'])

    def test_day_of_week_in_month(self):
        d = date(2007, 4, 15)
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('3', fmt['F'])

    def test_day_of_week_in_month_first(self):
        d = date(2007, 4, 1)
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('1', fmt['F'])

    def test_day_of_week_in_month_last(self):
        d = date(2007, 4, 29)
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('5', fmt['F'])

    def test_local_day_of_week(self):
        d = date(2007, 4, 1) # a sunday
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual('7', fmt['e']) # monday is first day of week
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('01', fmt['ee']) # sunday is first day of week
        fmt = dates.DateTimeFormat(d, locale='bn_BD')
        self.assertEqual('03', fmt['ee']) # friday is first day of week

        d = date(2007, 4, 2) # a monday
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual('1', fmt['e']) # monday is first day of week
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('02', fmt['ee']) # sunday is first day of week
        fmt = dates.DateTimeFormat(d, locale='bn_BD')
        self.assertEqual('04', fmt['ee']) # friday is first day of week

    def test_local_day_of_week_standalone(self):
        d = date(2007, 4, 1) # a sunday
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual('7', fmt['c']) # monday is first day of week
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('1', fmt['c']) # sunday is first day of week
        fmt = dates.DateTimeFormat(d, locale='bn_BD')
        self.assertEqual('3', fmt['c']) # friday is first day of week

        d = date(2007, 4, 2) # a monday
        fmt = dates.DateTimeFormat(d, locale='de_DE')
        self.assertEqual('1', fmt['c']) # monday is first day of week
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('2', fmt['c']) # sunday is first day of week
        fmt = dates.DateTimeFormat(d, locale='bn_BD')
        self.assertEqual('4', fmt['c']) # friday is first day of week

    def test_fractional_seconds(self):
        t = time(15, 30, 12, 34567)
        fmt = dates.DateTimeFormat(t, locale='en_US')
        self.assertEqual('3457', fmt['SSSS'])

    def test_fractional_seconds_zero(self):
        t = time(15, 30, 0)
        fmt = dates.DateTimeFormat(t, locale='en_US')
        self.assertEqual('0000', fmt['SSSS'])

    def test_milliseconds_in_day(self):
        t = time(15, 30, 12, 345000)
        fmt = dates.DateTimeFormat(t, locale='en_US')
        self.assertEqual('55812345', fmt['AAAA'])

    def test_milliseconds_in_day_zero(self):
        d = time(0, 0, 0)
        fmt = dates.DateTimeFormat(d, locale='en_US')
        self.assertEqual('0000', fmt['AAAA'])

    def test_timezone_rfc822(self):
        tz = timezone('Europe/Berlin')
        t = time(15, 30, tzinfo=tz)
        fmt = dates.DateTimeFormat(t, locale='de_DE')
        self.assertEqual('+0100', fmt['Z'])

    def test_timezone_gmt(self):
        tz = timezone('Europe/Berlin')
        t = time(15, 30, tzinfo=tz)
        fmt = dates.DateTimeFormat(t, locale='de_DE')
        self.assertEqual('GMT+01:00', fmt['ZZZZ'])

    def test_timezone_name(self):
        tz = timezone('Europe/Paris')
        dt = datetime(2007, 4, 1, 15, 30, tzinfo=tz)
        fmt = dates.DateTimeFormat(dt, locale='fr_FR')
        self.assertEqual('Heure : France', fmt['v'])

    def test_timezone_location_format(self):
        tz = timezone('Europe/Paris')
        dt = datetime(2007, 4, 1, 15, 30, tzinfo=tz)
        fmt = dates.DateTimeFormat(dt, locale='fr_FR')
        self.assertEqual('Heure : France', fmt['VVVV'])

    def test_timezone_walltime_short(self):
        tz = timezone('Europe/Paris')
        t = time(15, 30, tzinfo=tz)
        fmt = dates.DateTimeFormat(t, locale='fr_FR')
        self.assertEqual('Heure : France', fmt['v'])

    def test_timezone_walltime_long(self):
        tz = timezone('Europe/Paris')
        t = time(15, 30, tzinfo=tz)
        fmt = dates.DateTimeFormat(t, locale='fr_FR')
        self.assertEqual(u'heure de l\u2019Europe centrale', fmt['vvvv'])

    def test_hour_formatting(self):
        l = 'en_US'
        t = time(0, 0, 0)
        self.assertEqual(dates.format_time(t, 'h a', locale=l), '12 AM')
        self.assertEqual(dates.format_time(t, 'H', locale=l), '0')
        self.assertEqual(dates.format_time(t, 'k', locale=l), '24')
        self.assertEqual(dates.format_time(t, 'K a', locale=l), '0 AM')
        t = time(12, 0, 0)
        self.assertEqual(dates.format_time(t, 'h a', locale=l), '12 PM')
        self.assertEqual(dates.format_time(t, 'H', locale=l), '12')
        self.assertEqual(dates.format_time(t, 'k', locale=l), '12')
        self.assertEqual(dates.format_time(t, 'K a', locale=l), '0 PM')


class FormatDateTestCase(unittest.TestCase):

    def test_with_time_fields_in_pattern(self):
        self.assertRaises(AttributeError, dates.format_date, date(2007, 4, 1),
                          "yyyy-MM-dd HH:mm", locale='en_US')

    def test_with_time_fields_in_pattern_and_datetime_param(self):
        self.assertRaises(AttributeError, dates.format_date,
                          datetime(2007, 4, 1, 15, 30),
                          "yyyy-MM-dd HH:mm", locale='en_US')

    def test_with_day_of_year_in_pattern_and_datetime_param(self):
        # format_date should work on datetimes just as well (see #282)
        d = datetime(2007, 4, 1)
        self.assertEqual('14', dates.format_date(d, 'w', locale='en_US'))


class FormatDatetimeTestCase(unittest.TestCase):

    def test_with_float(self):
        d = datetime(2012, 4, 1, 15, 30, 29, tzinfo=timezone('UTC'))
        epoch = float(calendar.timegm(d.timetuple()))
        formatted_string = dates.format_datetime(epoch, format='long', locale='en_US')
        self.assertEqual(u'April 1, 2012 at 3:30:29 PM +0000', formatted_string)


class FormatTimeTestCase(unittest.TestCase):

    def test_with_naive_datetime_and_tzinfo(self):
        string = dates.format_time(datetime(2007, 4, 1, 15, 30),
                                   'long', tzinfo=timezone('US/Eastern'),
                                   locale='en')
        self.assertEqual('11:30:00 AM EDT', string)

    def test_with_float(self):
        d = datetime(2012, 4, 1, 15, 30, 29, tzinfo=timezone('UTC'))
        epoch = float(calendar.timegm(d.timetuple()))
        formatted_time = dates.format_time(epoch, format='long', locale='en_US')
        self.assertEqual(u'3:30:29 PM +0000', formatted_time)


    def test_with_date_fields_in_pattern(self):
        self.assertRaises(AttributeError, dates.format_time, date(2007, 4, 1),
                          "yyyy-MM-dd HH:mm", locale='en_US')

    def test_with_date_fields_in_pattern_and_datetime_param(self):
        self.assertRaises(AttributeError, dates.format_time,
                          datetime(2007, 4, 1, 15, 30),
                          "yyyy-MM-dd HH:mm", locale='en_US')


class FormatTimedeltaTestCase(unittest.TestCase):

    def test_zero_seconds(self):
        string = dates.format_timedelta(timedelta(seconds=0), locale='en')
        self.assertEqual('0 seconds', string)
        string = dates.format_timedelta(timedelta(seconds=0), locale='en',
                                        format='short')
        self.assertEqual('0 secs', string)
        string = dates.format_timedelta(timedelta(seconds=0),
                                        granularity='hour', locale='en')
        self.assertEqual('0 hours', string)
        string = dates.format_timedelta(timedelta(seconds=0),
                                        granularity='hour', locale='en',
                                        format='short')
        self.assertEqual('0 hrs', string)

    def test_small_value_with_granularity(self):
        string = dates.format_timedelta(timedelta(seconds=42),
                                        granularity='hour', locale='en')
        self.assertEqual('1 hour', string)
        string = dates.format_timedelta(timedelta(seconds=42),
                                        granularity='hour', locale='en',
                                        format='short')
        self.assertEqual('1 hr', string)

    def test_direction_adding(self):
        string = dates.format_timedelta(timedelta(hours=1),
                                        locale='en',
                                        add_direction=True)
        self.assertEqual('In 1 hour', string)
        string = dates.format_timedelta(timedelta(hours=-1),
                                        locale='en',
                                        add_direction=True)
        self.assertEqual('1 hour ago', string)


class TimeZoneAdjustTestCase(unittest.TestCase):
    def _utc(self):
        class EvilFixedOffsetTimezone(FixedOffsetTimezone):
            def localize(self, dt, is_dst=False):
                raise NotImplementedError()
        UTC = EvilFixedOffsetTimezone(0, 'UTC')
        # This is important to trigger the actual bug (#257)
        self.assertEqual(False, hasattr(UTC, 'normalize'))
        return UTC

    def test_can_format_time_with_non_pytz_timezone(self):
        # regression test for #257
        utc = self._utc()
        t = datetime(2007, 4, 1, 15, 30, tzinfo=utc)
        formatted_time = dates.format_time(t, 'long', tzinfo=utc, locale='en')
        self.assertEqual('3:30:00 PM +0000', formatted_time)


def test_get_period_names():
    assert dates.get_period_names(locale='en_US')['am'] == u'AM'


def test_get_day_names():
    assert dates.get_day_names('wide', locale='en_US')[1] == u'Tuesday'
    assert dates.get_day_names('abbreviated', locale='es')[1] == u'mar'
    de = dates.get_day_names('narrow', context='stand-alone', locale='de_DE')
    assert de[1] == u'D'


def test_get_month_names():
    assert dates.get_month_names('wide', locale='en_US')[1] == u'January'
    assert dates.get_month_names('abbreviated', locale='es')[1] == u'ene'
    de = dates.get_month_names('narrow', context='stand-alone', locale='de_DE')
    assert de[1] == u'J'


def test_get_quarter_names():
    assert dates.get_quarter_names('wide', locale='en_US')[1] == u'1st quarter'
    assert dates.get_quarter_names('abbreviated', locale='de_DE')[1] == u'Q1'


def test_get_era_names():
    assert dates.get_era_names('wide', locale='en_US')[1] == u'Anno Domini'
    assert dates.get_era_names('abbreviated', locale='de_DE')[1] == u'n. Chr.'


def test_get_date_format():
    us = dates.get_date_format(locale='en_US')
    assert us.pattern == u'MMM d, y'
    de = dates.get_date_format('full', locale='de_DE')
    assert de.pattern == u'EEEE, d. MMMM y'


def test_get_datetime_format():
    assert dates.get_datetime_format(locale='en_US') == u'{1}, {0}'


def test_get_time_format():
    assert dates.get_time_format(locale='en_US').pattern == u'h:mm:ss a'
    assert (dates.get_time_format('full', locale='de_DE').pattern ==
            u'HH:mm:ss zzzz')


def test_get_timezone_gmt():
    dt = datetime(2007, 4, 1, 15, 30)
    assert dates.get_timezone_gmt(dt, locale='en') == u'GMT+00:00'

    tz = timezone('America/Los_Angeles')
    dt = datetime(2007, 4, 1, 15, 30, tzinfo=tz)
    assert dates.get_timezone_gmt(dt, locale='en') == u'GMT-08:00'
    assert dates.get_timezone_gmt(dt, 'short', locale='en') == u'-0800'

    assert dates.get_timezone_gmt(dt, 'long', locale='fr_FR') == u'UTC-08:00'


def test_get_timezone_location():
    tz = timezone('America/St_Johns')
    assert (dates.get_timezone_location(tz, locale='de_DE') ==
            u"Kanada (St. John's) Zeit")
    tz = timezone('America/Mexico_City')
    assert (dates.get_timezone_location(tz, locale='de_DE') ==
            u'Mexiko (Mexiko-Stadt) Zeit')

    tz = timezone('Europe/Berlin')
    assert (dates.get_timezone_name(tz, locale='de_DE') ==
            u'Mitteleurop\xe4ische Zeit')


def test_get_timezone_name():
    dt = time(15, 30, tzinfo=timezone('America/Los_Angeles'))
    assert (dates.get_timezone_name(dt, locale='en_US') ==
            u'Pacific Standard Time')
    assert dates.get_timezone_name(dt, width='short', locale='en_US') == u'PST'

    tz = timezone('America/Los_Angeles')
    assert dates.get_timezone_name(tz, locale='en_US') == u'Pacific Time'
    assert dates.get_timezone_name(tz, 'short', locale='en_US') == u'PT'

    tz = timezone('Europe/Berlin')
    assert (dates.get_timezone_name(tz, locale='de_DE') ==
            u'Mitteleurop\xe4ische Zeit')
    assert (dates.get_timezone_name(tz, locale='pt_BR') ==
            u'Hor\xe1rio da Europa Central')

    tz = timezone('America/St_Johns')
    assert dates.get_timezone_name(tz, locale='de_DE') == u'Neufundland-Zeit'

    tz = timezone('America/Los_Angeles')
    assert dates.get_timezone_name(tz, locale='en', width='short',
                                   zone_variant='generic') == u'PT'
    assert dates.get_timezone_name(tz, locale='en', width='short',
                                   zone_variant='standard') == u'PST'
    assert dates.get_timezone_name(tz, locale='en', width='short',
                                   zone_variant='daylight') == u'PDT'
    assert dates.get_timezone_name(tz, locale='en', width='long',
                                   zone_variant='generic') == u'Pacific Time'
    assert dates.get_timezone_name(tz, locale='en', width='long',
                                   zone_variant='standard') == u'Pacific Standard Time'
    assert dates.get_timezone_name(tz, locale='en', width='long',
                                   zone_variant='daylight') == u'Pacific Daylight Time'


def test_format_date():
    d = date(2007, 4, 1)
    assert dates.format_date(d, locale='en_US') == u'Apr 1, 2007'
    assert (dates.format_date(d, format='full', locale='de_DE') ==
            u'Sonntag, 1. April 2007')
    assert (dates.format_date(d, "EEE, MMM d, ''yy", locale='en') ==
            u"Sun, Apr 1, '07")


def test_format_datetime():
    dt = datetime(2007, 4, 1, 15, 30)
    assert (dates.format_datetime(dt, locale='en_US') ==
            u'Apr 1, 2007, 3:30:00 PM')

    full = dates.format_datetime(dt, 'full', tzinfo=timezone('Europe/Paris'),
                                 locale='fr_FR')
    assert full == (u'dimanche 1 avril 2007 17:30:00 heure '
                    u'avanc\xe9e d\u2019Europe centrale')
    custom = dates.format_datetime(dt, "yyyy.MM.dd G 'at' HH:mm:ss zzz",
                                   tzinfo=timezone('US/Eastern'), locale='en')
    assert custom == u'2007.04.01 AD at 11:30:00 EDT'


def test_format_time():
    t = time(15, 30)
    assert dates.format_time(t, locale='en_US') == u'3:30:00 PM'
    assert dates.format_time(t, format='short', locale='de_DE') == u'15:30'

    assert (dates.format_time(t, "hh 'o''clock' a", locale='en') ==
            u"03 o'clock PM")

    t = datetime(2007, 4, 1, 15, 30)
    tzinfo = timezone('Europe/Paris')
    t = tzinfo.localize(t)
    fr = dates.format_time(t, format='full', tzinfo=tzinfo, locale='fr_FR')
    assert fr == u'15:30:00 heure avanc\xe9e d\u2019Europe centrale'
    custom = dates.format_time(t, "hh 'o''clock' a, zzzz",
                               tzinfo=timezone('US/Eastern'), locale='en')
    assert custom == u"09 o'clock AM, Eastern Daylight Time"

    t = time(15, 30)
    paris = dates.format_time(t, format='full',
                              tzinfo=timezone('Europe/Paris'), locale='fr_FR')
    assert paris == u'15:30:00 heure normale de l\u2019Europe centrale'
    us_east = dates.format_time(t, format='full',
                                tzinfo=timezone('US/Eastern'), locale='en_US')
    assert us_east == u'3:30:00 PM Eastern Standard Time'


def test_format_timedelta():
    assert (dates.format_timedelta(timedelta(weeks=12), locale='en_US')
            == u'3 months')
    assert (dates.format_timedelta(timedelta(seconds=1), locale='es')
            == u'1 segundo')

    assert (dates.format_timedelta(timedelta(hours=3), granularity='day',
                                   locale='en_US')
            == u'1 day')

    assert (dates.format_timedelta(timedelta(hours=23), threshold=0.9,
                                   locale='en_US')
            == u'1 day')
    assert (dates.format_timedelta(timedelta(hours=23), threshold=1.1,
                                   locale='en_US')
            == u'23 hours')


def test_parse_date():
    assert dates.parse_date('4/1/04', locale='en_US') == date(2004, 4, 1)
    assert dates.parse_date('01.04.2004', locale='de_DE') == date(2004, 4, 1)


def test_parse_time():
    assert dates.parse_time('15:30:00', locale='en_US') == time(15, 30)


def test_datetime_format_get_week_number():
    format = dates.DateTimeFormat(date(2006, 1, 8), Locale.parse('de_DE'))
    assert format.get_week_number(6) == 1

    format = dates.DateTimeFormat(date(2006, 1, 8), Locale.parse('en_US'))
    assert format.get_week_number(6) == 2


def test_parse_pattern():
    assert dates.parse_pattern("MMMMd").format == u'%(MMMM)s%(d)s'
    assert (dates.parse_pattern("MMM d, yyyy").format ==
            u'%(MMM)s %(d)s, %(yyyy)s')
    assert (dates.parse_pattern("H:mm' Uhr 'z").format ==
            u'%(H)s:%(mm)s Uhr %(z)s')
    assert dates.parse_pattern("hh' o''clock'").format == u"%(hh)s o'clock"

########NEW FILE########
__FILENAME__ = test_localedata
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import doctest
import unittest

from babel import localedata


class MergeResolveTestCase(unittest.TestCase):

    def test_merge_items(self):
        d = {1: 'foo', 3: 'baz'}
        localedata.merge(d, {1: 'Foo', 2: 'Bar'})
        self.assertEqual({1: 'Foo', 2: 'Bar', 3: 'baz'}, d)

    def test_merge_nested_dict(self):
        d1 = {'x': {'a': 1, 'b': 2, 'c': 3}}
        d2 = {'x': {'a': 1, 'b': 12, 'd': 14}}
        localedata.merge(d1, d2)
        self.assertEqual({
            'x': {'a': 1, 'b': 12, 'c': 3, 'd': 14}
        }, d1)

    def test_merge_nested_dict_no_overlap(self):
        d1 = {'x': {'a': 1, 'b': 2}}
        d2 = {'y': {'a': 11, 'b': 12}}
        localedata.merge(d1, d2)
        self.assertEqual({
            'x': {'a': 1, 'b': 2},
            'y': {'a': 11, 'b': 12}
        }, d1)

    def test_merge_with_alias_and_resolve(self):
        alias = localedata.Alias('x')
        d1 = {
            'x': {'a': 1, 'b': 2, 'c': 3},
            'y': alias
        }
        d2 = {
            'x': {'a': 1, 'b': 12, 'd': 14},
            'y': {'b': 22, 'e': 25}
        }
        localedata.merge(d1, d2)
        self.assertEqual({
            'x': {'a': 1, 'b': 12, 'c': 3, 'd': 14},
            'y': (alias, {'b': 22, 'e': 25})
        }, d1)
        d = localedata.LocaleDataDict(d1)
        self.assertEqual({
            'x': {'a': 1, 'b': 12, 'c': 3, 'd': 14},
            'y': {'a': 1, 'b': 22, 'c': 3, 'd': 14, 'e': 25}
        }, dict(d.items()))


def test_load():
    assert localedata.load('en_US')['languages']['sv'] == 'Swedish'
    assert localedata.load('en_US') is localedata.load('en_US')


def test_merge():
    d = {1: 'foo', 3: 'baz'}
    localedata.merge(d, {1: 'Foo', 2: 'Bar'})
    assert d == {1: 'Foo', 2: 'Bar', 3: 'baz'}

########NEW FILE########
__FILENAME__ = test_numbers
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

from decimal import Decimal
import unittest
import pytest

from datetime import date

from babel import numbers


class FormatDecimalTestCase(unittest.TestCase):

    def test_patterns(self):
        self.assertEqual(numbers.format_decimal(12345, '##0',
                         locale='en_US'), '12345')
        self.assertEqual(numbers.format_decimal(6.5, '0.00', locale='sv'),
                         '6,50')
        self.assertEqual(numbers.format_decimal(10.0**20,
                                                '#.00', locale='en_US'),
                         '100000000000000000000.00')
        # regression test for #183, fraction digits were not correctly cutted
        # if the input was a float value and the value had more than 7
        # significant digits
        self.assertEqual(u'12,345,678.05',
                         numbers.format_decimal(12345678.051, '#,##0.00',
                         locale='en_US'))

    def test_subpatterns(self):
        self.assertEqual(numbers.format_decimal(-12345, '#,##0.##;-#',
                         locale='en_US'), '-12,345')
        self.assertEqual(numbers.format_decimal(-12345, '#,##0.##;(#)',
                         locale='en_US'), '(12,345)')

    def test_default_rounding(self):
        """
        Testing Round-Half-Even (Banker's rounding)

        A '5' is rounded to the closest 'even' number
        """
        self.assertEqual(numbers.format_decimal(5.5, '0', locale='sv'), '6')
        self.assertEqual(numbers.format_decimal(6.5, '0', locale='sv'), '6')
        self.assertEqual(numbers.format_decimal(6.5, '0', locale='sv'), '6')
        self.assertEqual(numbers.format_decimal(1.2325, locale='sv'), '1,232')
        self.assertEqual(numbers.format_decimal(1.2335, locale='sv'), '1,234')

    def test_significant_digits(self):
        """Test significant digits patterns"""
        self.assertEqual(numbers.format_decimal(123004, '@@',locale='en_US'),
                        '120000')
        self.assertEqual(numbers.format_decimal(1.12, '@', locale='sv'), '1')
        self.assertEqual(numbers.format_decimal(1.1, '@@', locale='sv'), '1,1')
        self.assertEqual(numbers.format_decimal(1.1, '@@@@@##', locale='sv'),
                         '1,1000')
        self.assertEqual(numbers.format_decimal(0.0001, '@@@', locale='sv'),
                         '0,000100')
        self.assertEqual(numbers.format_decimal(0.0001234, '@@@', locale='sv'),
                         '0,000123')
        self.assertEqual(numbers.format_decimal(0.0001234, '@@@#',locale='sv'),
                         '0,0001234')
        self.assertEqual(numbers.format_decimal(0.0001234, '@@@#',locale='sv'),
                         '0,0001234')
        self.assertEqual(numbers.format_decimal(0.12345, '@@@',locale='sv'),
                         '0,123')
        self.assertEqual(numbers.format_decimal(3.14159, '@@##',locale='sv'),
                         '3,142')
        self.assertEqual(numbers.format_decimal(1.23004, '@@##',locale='sv'),
                         '1,23')
        self.assertEqual(numbers.format_decimal(1230.04, '@@,@@',locale='en_US'),
                         '12,30')
        self.assertEqual(numbers.format_decimal(123.41, '@@##',locale='en_US'),
                         '123.4')
        self.assertEqual(numbers.format_decimal(1, '@@',locale='en_US'),
                         '1.0')
        self.assertEqual(numbers.format_decimal(0, '@',locale='en_US'),
                         '0')
        self.assertEqual(numbers.format_decimal(0.1, '@',locale='en_US'),
                         '0.1')
        self.assertEqual(numbers.format_decimal(0.1, '@#',locale='en_US'),
                         '0.1')
        self.assertEqual(numbers.format_decimal(0.1, '@@', locale='en_US'),
                         '0.10')

    def test_decimals(self):
        """Test significant digits patterns"""
        self.assertEqual(numbers.format_decimal(Decimal('1.2345'),
                                                '#.00', locale='en_US'),
                         '1.23')
        self.assertEqual(numbers.format_decimal(Decimal('1.2345000'),
                                                '#.00', locale='en_US'),
                         '1.23')
        self.assertEqual(numbers.format_decimal(Decimal('1.2345000'),
                                                '@@', locale='en_US'),
                         '1.2')
        self.assertEqual(numbers.format_decimal(Decimal('12345678901234567890.12345'),
                                                '#.00', locale='en_US'),
                         '12345678901234567890.12')

    def test_scientific_notation(self):
        fmt = numbers.format_scientific(0.1, '#E0', locale='en_US')
        self.assertEqual(fmt, '1E-1')
        fmt = numbers.format_scientific(0.01, '#E0', locale='en_US')
        self.assertEqual(fmt, '1E-2')
        fmt = numbers.format_scientific(10, '#E0', locale='en_US')
        self.assertEqual(fmt, '1E1')
        fmt = numbers.format_scientific(1234, '0.###E0', locale='en_US')
        self.assertEqual(fmt, '1.234E3')
        fmt = numbers.format_scientific(1234, '0.#E0', locale='en_US')
        self.assertEqual(fmt, '1.2E3')
        # Exponent grouping
        fmt = numbers.format_scientific(12345, '##0.####E0', locale='en_US')
        self.assertEqual(fmt, '12.345E3')
        # Minimum number of int digits
        fmt = numbers.format_scientific(12345, '00.###E0', locale='en_US')
        self.assertEqual(fmt, '12.345E3')
        fmt = numbers.format_scientific(-12345.6, '00.###E0', locale='en_US')
        self.assertEqual(fmt, '-12.346E3')
        fmt = numbers.format_scientific(-0.01234, '00.###E0', locale='en_US')
        self.assertEqual(fmt, '-12.34E-3')
        # Custom pattern suffic
        fmt = numbers.format_scientific(123.45, '#.##E0 m/s', locale='en_US')
        self.assertEqual(fmt, '1.23E2 m/s')
        # Exponent patterns
        fmt = numbers.format_scientific(123.45, '#.##E00 m/s', locale='en_US')
        self.assertEqual(fmt, '1.23E02 m/s')
        fmt = numbers.format_scientific(0.012345, '#.##E00 m/s', locale='en_US')
        self.assertEqual(fmt, '1.23E-02 m/s')
        fmt = numbers.format_scientific(Decimal('12345'), '#.##E+00 m/s',
        locale='en_US')
        self.assertEqual(fmt, '1.23E+04 m/s')
        # 0 (see ticket #99)
        fmt = numbers.format_scientific(0, '#E0', locale='en_US')
        self.assertEqual(fmt, '0E0')

    def test_formatting_of_very_small_decimals(self):
        # previously formatting very small decimals could lead to a type error
        # because the Decimal->string conversion was too simple (see #214)
        number = Decimal("7E-7")
        fmt = numbers.format_decimal(number, format="@@@", locale='en_US')
        self.assertEqual('0.000000700', fmt)


class BankersRoundTestCase(unittest.TestCase):
    def test_round_to_nearest_integer(self):
        self.assertEqual(1, numbers.bankersround(Decimal('0.5001')))

    def test_round_to_even_for_two_nearest_integers(self):
        self.assertEqual(0, numbers.bankersround(Decimal('0.5')))
        self.assertEqual(2, numbers.bankersround(Decimal('1.5')))
        self.assertEqual(-2, numbers.bankersround(Decimal('-2.5')))

        self.assertEqual(0, numbers.bankersround(Decimal('0.05'), ndigits=1))
        self.assertEqual(Decimal('0.2'), numbers.bankersround(Decimal('0.15'), ndigits=1))


class NumberParsingTestCase(unittest.TestCase):
    def test_can_parse_decimals(self):
        self.assertEqual(Decimal('1099.98'),
            numbers.parse_decimal('1,099.98', locale='en_US'))
        self.assertEqual(Decimal('1099.98'),
            numbers.parse_decimal('1.099,98', locale='de'))
        self.assertRaises(numbers.NumberFormatError,
                          lambda: numbers.parse_decimal('2,109,998', locale='de'))


def test_get_currency_name():
    assert numbers.get_currency_name('USD', locale='en_US') == u'US Dollar'
    assert numbers.get_currency_name('USD', count=2, locale='en_US') == u'US dollars'


def test_get_currency_symbol():
    assert numbers.get_currency_symbol('USD', 'en_US') == u'$'


def test_get_territory_currencies():
    assert numbers.get_territory_currencies('AT', date(1995, 1, 1)) == ['ATS']
    assert numbers.get_territory_currencies('AT', date(2011, 1, 1)) == ['EUR']

    assert numbers.get_territory_currencies('US', date(2013, 1, 1)) == ['USD']
    assert sorted(numbers.get_territory_currencies('US', date(2013, 1, 1),
        non_tender=True)) == ['USD', 'USN', 'USS']

    assert numbers.get_territory_currencies('US', date(2013, 1, 1),
        include_details=True) == [{
            'currency': 'USD',
            'from': date(1792, 1, 1),
            'to': None,
            'tender': True
        }]

    assert numbers.get_territory_currencies('LS', date(2013, 1, 1)) == ['ZAR', 'LSL']

    assert numbers.get_territory_currencies('QO', date(2013, 1, 1)) == []


def test_get_decimal_symbol():
    assert numbers.get_decimal_symbol('en_US') == u'.'


def test_get_plus_sign_symbol():
    assert numbers.get_plus_sign_symbol('en_US') == u'+'


def test_get_minus_sign_symbol():
    assert numbers.get_minus_sign_symbol('en_US') == u'-'
    assert numbers.get_minus_sign_symbol('nl_NL') == u'-'


def test_get_exponential_symbol():
    assert numbers.get_exponential_symbol('en_US') == u'E'


def test_get_group_symbol():
    assert numbers.get_group_symbol('en_US') == u','


def test_format_number():
    assert numbers.format_number(1099, locale='en_US') == u'1,099'
    assert numbers.format_number(1099, locale='de_DE') == u'1.099'


def test_format_decimal():
    assert numbers.format_decimal(1.2345, locale='en_US') == u'1.234'
    assert numbers.format_decimal(1.2346, locale='en_US') == u'1.235'
    assert numbers.format_decimal(-1.2346, locale='en_US') == u'-1.235'
    assert numbers.format_decimal(1.2345, locale='sv_SE') == u'1,234'
    assert numbers.format_decimal(1.2345, locale='de') == u'1,234'
    assert numbers.format_decimal(12345.5, locale='en_US') == u'12,345.5'


def test_format_currency():
    assert (numbers.format_currency(1099.98, 'USD', locale='en_US')
            == u'$1,099.98')
    assert (numbers.format_currency(1099.98, 'USD', locale='es_CO')
            == u'1.099,98\xa0US$')
    assert (numbers.format_currency(1099.98, 'EUR', locale='de_DE')
            == u'1.099,98\xa0\u20ac')
    assert (numbers.format_currency(1099.98, 'EUR', u'\xa4\xa4 #,##0.00',
                                    locale='en_US')
            == u'EUR 1,099.98')
    assert (numbers.format_currency(1099.98, 'EUR', locale='nl_NL')
            != numbers.format_currency(-1099.98, 'EUR', locale='nl_NL'))


def test_format_percent():
    assert numbers.format_percent(0.34, locale='en_US') == u'34%'
    assert numbers.format_percent(25.1234, locale='en_US') == u'2,512%'
    assert (numbers.format_percent(25.1234, locale='sv_SE')
            == u'2\xa0512\xa0%')
    assert (numbers.format_percent(25.1234, u'#,##0\u2030', locale='en_US')
            == u'25,123\u2030')


def test_scientific_exponent_displayed_as_integer():
    assert numbers.format_scientific(100000, locale='en_US') == u'1E5'


def test_format_scientific():
    assert numbers.format_scientific(10000, locale='en_US') == u'1E4'
    assert (numbers.format_scientific(1234567, u'##0E00', locale='en_US')
            == u'1.23E06')


def test_parse_number():
    assert numbers.parse_number('1,099', locale='en_US') == 1099
    assert numbers.parse_number('1.099', locale='de_DE') == 1099

    with pytest.raises(numbers.NumberFormatError) as excinfo:
        numbers.parse_number('1.099,98', locale='de')
    assert excinfo.value.args[0] == "'1.099,98' is not a valid number"


def test_parse_decimal():
    assert (numbers.parse_decimal('1,099.98', locale='en_US')
            == Decimal('1099.98'))
    assert numbers.parse_decimal('1.099,98', locale='de') == Decimal('1099.98')

    with pytest.raises(numbers.NumberFormatError) as excinfo:
        numbers.parse_decimal('2,109,998', locale='de')
    assert excinfo.value.args[0] == "'2,109,998' is not a valid decimal number"


def test_bankersround():
    assert numbers.bankersround(5.5, 0) == 6.0
    assert numbers.bankersround(6.5, 0) == 6.0
    assert numbers.bankersround(-6.5, 0) == -6.0
    assert numbers.bankersround(1234.0, -2) == 1200.0


def test_parse_grouping():
    assert numbers.parse_grouping('##') == (1000, 1000)
    assert numbers.parse_grouping('#,###') == (3, 3)
    assert numbers.parse_grouping('#,####,###') == (3, 4)


def test_parse_pattern():
    assert numbers.parse_pattern(u'¤#,##0.00;(¤#,##0.00)').suffix == (u'', u')')
    assert numbers.parse_pattern(u'¤ #,##0.00;¤ #,##0.00-').suffix == (u'', u'-')

########NEW FILE########
__FILENAME__ = test_plural
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import doctest
import unittest

from babel import plural


class test_plural_rule():
    rule = plural.PluralRule({'one': 'n is 1'})
    assert rule(1) == 'one'
    assert rule(2) == 'other'

    rule = plural.PluralRule({'one': 'n is 1'})
    assert rule.rules == {'one': 'n is 1'}


def test_to_javascript():
    assert (plural.to_javascript({'one': 'n is 1'})
            == "(function(n) { return (n == 1) ? 'one' : 'other'; })")


def test_to_python():
    func = plural.to_python({'one': 'n is 1', 'few': 'n in 2..4'})
    assert func(1) == 'one'
    assert func(3) == 'few'

    func = plural.to_python({'one': 'n in 1,11', 'few': 'n in 3..10,13..19'})
    assert func(11) == 'one'
    assert func(15) == 'few'


def test_to_gettext():
    assert (plural.to_gettext({'one': 'n is 1', 'two': 'n is 2'})
            == 'nplurals=3; plural=((n == 1) ? 0 : (n == 2) ? 1 : 2)')


def test_in_range_list():
    assert plural.in_range_list(1, [(1, 3)])
    assert plural.in_range_list(3, [(1, 3)])
    assert plural.in_range_list(3, [(1, 3), (5, 8)])
    assert not plural.in_range_list(1.2, [(1, 4)])
    assert not plural.in_range_list(10, [(1, 4)])
    assert not plural.in_range_list(10, [(1, 4), (6, 8)])


def test_within_range_list():
    assert plural.within_range_list(1, [(1, 3)])
    assert plural.within_range_list(1.0, [(1, 3)])
    assert plural.within_range_list(1.2, [(1, 4)])
    assert plural.within_range_list(8.8, [(1, 4), (7, 15)])
    assert not plural.within_range_list(10, [(1, 4)])
    assert not plural.within_range_list(10.5, [(1, 4), (20, 30)])


def test_cldr_modulo():
    assert plural.cldr_modulo(-3, 5) == -3
    assert plural.cldr_modulo(-3, -5) == -3
    assert plural.cldr_modulo(3, 5) == 3


def test_plural_within_rules():
    p = plural.PluralRule({'one': 'n is 1', 'few': 'n within 2,4,7..9'})
    assert repr(p) == "<PluralRule 'one: n is 1, few: n within 2,4,7..9'>"
    assert plural.to_javascript(p) == (
        "(function(n) { "
            "return ((n == 2) || (n == 4) || (n >= 7 && n <= 9))"
            " ? 'few' : (n == 1) ? 'one' : 'other'; })")
    assert plural.to_gettext(p) == (
        'nplurals=3; plural=(((n == 2) || (n == 4) || (n >= 7 && n <= 9))'
        ' ? 1 : (n == 1) ? 0 : 2)')
    assert p(0) == 'other'
    assert p(1) == 'one'
    assert p(2) == 'few'
    assert p(3) == 'other'
    assert p(4) == 'few'
    assert p(5) == 'other'
    assert p(6) == 'other'
    assert p(7) == 'few'
    assert p(8) == 'few'
    assert p(9) == 'few'


def test_locales_with_no_plural_rules_have_default():
    from babel import Locale
    aa_plural = Locale.parse('aa').plural_form
    assert aa_plural(1) == 'other'
    assert aa_plural(2) == 'other'
    assert aa_plural(15) == 'other'

########NEW FILE########
__FILENAME__ = test_support
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import inspect
import os
import shutil
import tempfile
import unittest
import pytest
from datetime import date, datetime, timedelta

from babel import support
from babel.messages import Catalog
from babel.messages.mofile import write_mo
from babel._compat import BytesIO


@pytest.mark.usefixtures("os_environ")
class TranslationsTestCase(unittest.TestCase):

    def setUp(self):
        # Use a locale which won't fail to run the tests
        os.environ['LANG'] = 'en_US.UTF-8'
        messages1 = [
            ('foo', {'string': 'Voh'}),
            ('foo', {'string': 'VohCTX', 'context': 'foo'}),
            (('foo1', 'foos1'), {'string': ('Voh1', 'Vohs1')}),
            (('foo1', 'foos1'), {'string': ('VohCTX1', 'VohsCTX1'), 'context': 'foo'}),
        ]
        messages2 = [
            ('foo', {'string': 'VohD'}),
            ('foo', {'string': 'VohCTXD', 'context': 'foo'}),
            (('foo1', 'foos1'), {'string': ('VohD1', 'VohsD1')}),
            (('foo1', 'foos1'), {'string': ('VohCTXD1', 'VohsCTXD1'), 'context': 'foo'}),
        ]
        catalog1 = Catalog(locale='en_GB', domain='messages')
        catalog2 = Catalog(locale='en_GB', domain='messages1')
        for ids, kwargs in messages1:
            catalog1.add(ids, **kwargs)
        for ids, kwargs in messages2:
            catalog2.add(ids, **kwargs)
        catalog1_fp = BytesIO()
        catalog2_fp = BytesIO()
        write_mo(catalog1_fp, catalog1)
        catalog1_fp.seek(0)
        write_mo(catalog2_fp, catalog2)
        catalog2_fp.seek(0)
        translations1 = support.Translations(catalog1_fp)
        translations2 = support.Translations(catalog2_fp, domain='messages1')
        self.translations = translations1.add(translations2, merge=False)

    def assertEqualTypeToo(self, expected, result):
        self.assertEqual(expected, result)
        assert type(expected) == type(result), "instance type's do not " + \
            "match: %r!=%r" % (type(expected), type(result))

    def test_pgettext(self):
        self.assertEqualTypeToo('Voh', self.translations.gettext('foo'))
        self.assertEqualTypeToo('VohCTX', self.translations.pgettext('foo',
                                                                     'foo'))

    def test_upgettext(self):
        self.assertEqualTypeToo(u'Voh', self.translations.ugettext('foo'))
        self.assertEqualTypeToo(u'VohCTX', self.translations.upgettext('foo',
                                                                       'foo'))

    def test_lpgettext(self):
        self.assertEqualTypeToo(b'Voh', self.translations.lgettext('foo'))
        self.assertEqualTypeToo(b'VohCTX', self.translations.lpgettext('foo',
                                                                       'foo'))

    def test_npgettext(self):
        self.assertEqualTypeToo('Voh1',
                                self.translations.ngettext('foo1', 'foos1', 1))
        self.assertEqualTypeToo('Vohs1',
                                self.translations.ngettext('foo1', 'foos1', 2))
        self.assertEqualTypeToo('VohCTX1',
                                self.translations.npgettext('foo', 'foo1',
                                                            'foos1', 1))
        self.assertEqualTypeToo('VohsCTX1',
                                self.translations.npgettext('foo', 'foo1',
                                                            'foos1', 2))

    def test_unpgettext(self):
        self.assertEqualTypeToo(u'Voh1',
                                self.translations.ungettext('foo1', 'foos1', 1))
        self.assertEqualTypeToo(u'Vohs1',
                                self.translations.ungettext('foo1', 'foos1', 2))
        self.assertEqualTypeToo(u'VohCTX1',
                                self.translations.unpgettext('foo', 'foo1',
                                                             'foos1', 1))
        self.assertEqualTypeToo(u'VohsCTX1',
                                self.translations.unpgettext('foo', 'foo1',
                                                             'foos1', 2))

    def test_lnpgettext(self):
        self.assertEqualTypeToo(b'Voh1',
                                self.translations.lngettext('foo1', 'foos1', 1))
        self.assertEqualTypeToo(b'Vohs1',
                                self.translations.lngettext('foo1', 'foos1', 2))
        self.assertEqualTypeToo(b'VohCTX1',
                                self.translations.lnpgettext('foo', 'foo1',
                                                             'foos1', 1))
        self.assertEqualTypeToo(b'VohsCTX1',
                                self.translations.lnpgettext('foo', 'foo1',
                                                             'foos1', 2))

    def test_dpgettext(self):
        self.assertEqualTypeToo(
            'VohD', self.translations.dgettext('messages1', 'foo'))
        self.assertEqualTypeToo(
            'VohCTXD', self.translations.dpgettext('messages1', 'foo', 'foo'))

    def test_dupgettext(self):
        self.assertEqualTypeToo(
            u'VohD', self.translations.dugettext('messages1', 'foo'))
        self.assertEqualTypeToo(
            u'VohCTXD', self.translations.dupgettext('messages1', 'foo', 'foo'))

    def test_ldpgettext(self):
        self.assertEqualTypeToo(
            b'VohD', self.translations.ldgettext('messages1', 'foo'))
        self.assertEqualTypeToo(
            b'VohCTXD', self.translations.ldpgettext('messages1', 'foo', 'foo'))

    def test_dnpgettext(self):
        self.assertEqualTypeToo(
            'VohD1', self.translations.dngettext('messages1', 'foo1', 'foos1', 1))
        self.assertEqualTypeToo(
            'VohsD1', self.translations.dngettext('messages1', 'foo1', 'foos1', 2))
        self.assertEqualTypeToo(
            'VohCTXD1', self.translations.dnpgettext('messages1', 'foo', 'foo1',
                                                     'foos1', 1))
        self.assertEqualTypeToo(
            'VohsCTXD1', self.translations.dnpgettext('messages1', 'foo', 'foo1',
                                                      'foos1', 2))

    def test_dunpgettext(self):
        self.assertEqualTypeToo(
            u'VohD1', self.translations.dungettext('messages1', 'foo1', 'foos1', 1))
        self.assertEqualTypeToo(
            u'VohsD1', self.translations.dungettext('messages1', 'foo1', 'foos1', 2))
        self.assertEqualTypeToo(
            u'VohCTXD1', self.translations.dunpgettext('messages1', 'foo', 'foo1',
                                                       'foos1', 1))
        self.assertEqualTypeToo(
            u'VohsCTXD1', self.translations.dunpgettext('messages1', 'foo', 'foo1',
                                                        'foos1', 2))

    def test_ldnpgettext(self):
        self.assertEqualTypeToo(
            b'VohD1', self.translations.ldngettext('messages1', 'foo1', 'foos1', 1))
        self.assertEqualTypeToo(
            b'VohsD1', self.translations.ldngettext('messages1', 'foo1', 'foos1', 2))
        self.assertEqualTypeToo(
            b'VohCTXD1', self.translations.ldnpgettext('messages1', 'foo', 'foo1',
                                                       'foos1', 1))
        self.assertEqualTypeToo(
            b'VohsCTXD1', self.translations.ldnpgettext('messages1', 'foo', 'foo1',
                                                        'foos1', 2))

    def test_load(self):
        tempdir = tempfile.mkdtemp()
        try:
            messages_dir = os.path.join(tempdir, 'fr', 'LC_MESSAGES')
            os.makedirs(messages_dir)
            catalog = Catalog(locale='fr', domain='messages')
            catalog.add('foo', 'bar')
            with open(os.path.join(messages_dir, 'messages.mo'), 'wb') as f:
                write_mo(f, catalog)

            translations = support.Translations.load(tempdir, locales=('fr',), domain='messages')
            self.assertEqual('bar', translations.gettext('foo'))
        finally:
            shutil.rmtree(tempdir)


class NullTranslationsTestCase(unittest.TestCase):
    def setUp(self):
        fp = BytesIO()
        write_mo(fp, Catalog(locale='de'))
        fp.seek(0)
        self.translations = support.Translations(fp=fp)
        self.null_translations = support.NullTranslations(fp=fp)

    def method_names(self):
        return [name for name in dir(self.translations) if 'gettext' in name]

    def test_same_methods(self):
        for name in self.method_names():
            if not hasattr(self.null_translations, name):
                self.fail('NullTranslations does not provide method %r' % name)

    def test_method_signature_compatibility(self):
        for name in self.method_names():
            translations_method = getattr(self.translations, name)
            null_method = getattr(self.null_translations, name)
            signature = inspect.getargspec
            self.assertEqual(signature(translations_method),
                             signature(null_method))

    def test_same_return_values(self):
        data = {
            'message': u'foo', 'domain': u'domain', 'context': 'tests',
            'singular': u'bar', 'plural': u'baz', 'num': 1,
            'msgid1': u'bar', 'msgid2': u'baz', 'n': 1,
        }
        for name in self.method_names():
            method = getattr(self.translations, name)
            null_method = getattr(self.null_translations, name)
            signature = inspect.getargspec(method)
            parameter_names = [name for name in signature[0] if name != 'self']
            values = [data[name] for name in parameter_names]
            self.assertEqual(method(*values), null_method(*values))


class LazyProxyTestCase(unittest.TestCase):
    def test_proxy_caches_result_of_function_call(self):
        self.counter = 0
        def add_one():
            self.counter += 1
            return self.counter
        proxy = support.LazyProxy(add_one)
        self.assertEqual(1, proxy.value)
        self.assertEqual(1, proxy.value)

    def test_can_disable_proxy_cache(self):
        self.counter = 0
        def add_one():
            self.counter += 1
            return self.counter
        proxy = support.LazyProxy(add_one, enable_cache=False)
        self.assertEqual(1, proxy.value)
        self.assertEqual(2, proxy.value)


def test_format_date():
    fmt = support.Format('en_US')
    assert fmt.date(date(2007, 4, 1)) == 'Apr 1, 2007'


def test_format_datetime():
    from pytz import timezone
    fmt = support.Format('en_US', tzinfo=timezone('US/Eastern'))
    when = datetime(2007, 4, 1, 15, 30)
    assert fmt.datetime(when) == 'Apr 1, 2007, 11:30:00 AM'


def test_format_time():
    from pytz import timezone
    fmt = support.Format('en_US', tzinfo=timezone('US/Eastern'))
    assert fmt.time(datetime(2007, 4, 1, 15, 30)) == '11:30:00 AM'


def test_format_timedelta():
    fmt = support.Format('en_US')
    assert fmt.timedelta(timedelta(weeks=11)) == '3 months'


def test_format_number():
    fmt = support.Format('en_US')
    assert fmt.number(1099) == '1,099'


def test_format_decimal():
    fmt = support.Format('en_US')
    assert fmt.decimal(1.2345) == '1.234'


def test_format_percent():
    fmt = support.Format('en_US')
    assert fmt.percent(0.34) == '34%'


def test_lazy_proxy():
    def greeting(name='world'):
        return u'Hello, %s!' % name
    lazy_greeting = support.LazyProxy(greeting, name='Joe')
    assert str(lazy_greeting) == u"Hello, Joe!"
    assert u'  ' + lazy_greeting == u'  Hello, Joe!'
    assert u'(%s)' % lazy_greeting == u'(Hello, Joe!)'

    greetings = [
        support.LazyProxy(greeting, 'world'),
        support.LazyProxy(greeting, 'Joe'),
        support.LazyProxy(greeting, 'universe'),
    ]
    greetings.sort()
    assert [str(g) for g in greetings] == [
        u"Hello, Joe!",
        u"Hello, universe!",
        u"Hello, world!",
    ]

########NEW FILE########
__FILENAME__ = test_util
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2011 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import doctest
import unittest

from babel import util


def test_distinct():
    assert list(util.distinct([1, 2, 1, 3, 4, 4])) == [1, 2, 3, 4]
    assert list(util.distinct('foobar')) == ['f', 'o', 'b', 'a', 'r']


def test_pathmatch():
    assert util.pathmatch('**.py', 'bar.py')
    assert util.pathmatch('**.py', 'foo/bar/baz.py')
    assert not util.pathmatch('**.py', 'templates/index.html')
    assert util.pathmatch('**/templates/*.html', 'templates/index.html')
    assert not util.pathmatch('**/templates/*.html', 'templates/foo/bar.html')

########NEW FILE########
