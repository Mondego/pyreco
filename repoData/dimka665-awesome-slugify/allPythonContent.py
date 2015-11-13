__FILENAME__ = alt_translates
# coding=utf8

CYRILLIC = {       # instead of:
    u'ё': u'e',    # io / yo
    u'у': u'y',    # u
    u'х': u'h',    # kh
    u'щ': u'sch',  # shch
    u'ю': u'u',    # iu / yu
    u'я': u'ya',   # ia
}

GERMAN = {         # instead of:
    u'ä': u'ae',   # a
    u'ö': u'oe',   # o
    u'ü': u'ue',   # u
}

GREEK = {          # instead of:
    u'Ξ': u'X',    # Ks
    u'χ': u'ch',   # kh

    u'ϒ': u'Y',    # U
    u'υ': u'y',    # u
    u'ύ': u'y',    # ...
    u'ϋ': u'y',
    u'ΰ': u'y',
}

########NEW FILE########
__FILENAME__ = main
# coding=utf8

import sys

from unidecode import unidecode
import regex as re


re.DEFAULT_VERSION = re.V1  # Version 1 behaviour: nested sets and set operations are supported


if sys.version_info[0] == 2:
    TEXT_TYPE = unicode  # Python 2
else:
    TEXT_TYPE = str  # Python 3


def join_words(words, separator, max_length=None):

    if not max_length:
        return separator.join(words)

    words = iter(words)   # List to Generator
    try:
        text = next(words)
    except StopIteration:
        return u''

    for word in words:
        if len(text + separator + word) <= max_length:
            text += separator + word

    return text[:max_length]

# uppercase letters to translate to uppercase letters, NOT camelcase
UPPER_TO_UPPER_LETTERS_RE = \
    u'''
    (
            \p{Uppercase_Letter} {2,}                          # 2 or more adjacent letters - UP always
        |
            \p{Uppercase_Letter}                               # target one uppercase letter, then
                (?=
                    [^\p{Lowercase_Letter}…\p{Term}--,،﹐，]+    # not chars breaks possible UP (…abc.?!:;)
                    \p{Uppercase_Letter} {2}                   # and 2 uppercase letters
                )
        |
            (?<=
                \p{Uppercase_Letter} {2}                       # 2 uppercase letters
                [^\p{Lowercase_Letter}…\p{Term}--,،﹐，]+       # not chars breaks possible UP (…abc.?!:;), then
            )
            \p{Uppercase_Letter}                               # target one uppercase letter, then
            (?!
                    \p{Lowercase_Letter}                       # not lowercase letter
                |
                    […\p{Term}--,،﹐，]\p{Uppercase_Letter}      # and not dot (.?…!:;) with uppercase letter
            )
    )
    '''


class Slugify(object):

    upper_to_upper_letters_re = re.compile(UPPER_TO_UPPER_LETTERS_RE, re.VERBOSE)
    _safe_chars = ''
    _stop_words = ()

    def __init__(self, pretranslate=None, translate=unidecode, safe_chars='', stop_words=(),
                 to_lower=False, max_length=None, separator=u'-', capitalize=False):

        self.pretranslate = pretranslate
        self.translate = translate
        self.safe_chars = safe_chars
        self.stop_words = stop_words

        self.to_lower = to_lower
        self.max_length = max_length
        self.separator = separator
        self.capitalize = capitalize

    def pretranslate_dict_to_function(self, convert_dict):

        # add uppercase letters
        for letter, translation in list(convert_dict.items()):
            letter_upper = letter.upper()
            if letter_upper != letter and letter_upper not in convert_dict:
                convert_dict[letter_upper] = translation.capitalize()

        self.convert_dict = convert_dict
        PRETRANSLATE = re.compile(u'(\L<options>)', options=convert_dict)

        # translate some letters before translating
        return lambda text: PRETRANSLATE.sub(lambda m: convert_dict[m.group(1)], text)

    def set_pretranslate(self, pretranslate):
        if isinstance(pretranslate, dict):
            pretranslate = self.pretranslate_dict_to_function(pretranslate)

        elif pretranslate is None:
            pretranslate = lambda text: text

        elif not callable(pretranslate):
            error_message = u"Keyword argument 'pretranslate' must be dict, None or callable. Not {0.__class__.__name__}".format(pretranslate)
            raise ValueError(error_message)

        self._pretranslate = pretranslate

    pretranslate = property(fset=set_pretranslate)

    def set_translate(self, func):
        if func:
            self._translate = func
        else:
            self._translate = lambda text: text

    translate = property(fset=set_translate)

    def set_safe_chars(self, safe_chars):
        self._safe_chars = safe_chars
        self.apostrophe_is_not_safe = "'" not in safe_chars
        self.calc_unwanted_chars_re()

    safe_chars = property(fset=set_safe_chars)

    def set_stop_words(self, stop_words):
        self._stop_words = tuple(stop_words)
        self.calc_unwanted_chars_re()

    stop_words = property(fset=set_stop_words)

    def calc_unwanted_chars_re(self):
        sanitize_re = u'[^\p{{AlNum}}{safe_chars}]+'.format(safe_chars=re.escape(self._safe_chars or ''))

        if self._stop_words:
            sanitize_re += u'|(?<!\p{AlNum})(?:\L<stop_words>)(?!\p{AlNum})'
            self.sanitize_re = re.compile(sanitize_re, re.IGNORECASE, stop_words=self._stop_words)
        else:
            self.sanitize_re = re.compile(sanitize_re)

    def sanitize(self, text):
        if self.apostrophe_is_not_safe:
            text = text.replace("'", '').strip()  # remove '
        return filter(None, self.sanitize_re.split(text))  # split by unwanted characters

    def __call__(self, text, **kwargs):

        max_length = kwargs.get('max_length', self.max_length)
        separator = kwargs.get('separator', self.separator)

        if not isinstance(text, TEXT_TYPE):
            text = text.decode('utf8', 'ignore')

        if kwargs.get('to_lower', self.to_lower):
            text = text.lower()
            text = self._pretranslate(text)
            text = self._translate(text)

        else:
            text_parts = self.upper_to_upper_letters_re.split(text)

            for position, text_part in enumerate(text_parts):
                text_part = self._pretranslate(text_part)
                text_part = self._translate(text_part)
                if position % 2:
                    text_part = text_part.upper()

                text_parts[position] = text_part

            text = u''.join(text_parts)

        words = self.sanitize(text)
        text = join_words(words, separator, max_length)

        if text and kwargs.get('capitalize', self.capitalize):
            text = text[0].upper() + text[1:]

        return text

# \p{SB=AT} = '.․﹒．'
# \p{SB=ST} = '!?՜՞։؟۔܀܁܂߹।॥၊။።፧፨᙮᜵᜶‼‽⁇⁈⁉⸮。꓿꘎꘏꤯﹖﹗！？｡'
# \p{Term}  = '!,.:;?;·։׃،؛؟۔܀܁܂܃܄܅܆܇܈܉܊܌߸߹।॥๚๛༈།༎༏༐༑༒၊။፡።፣፤፥፦፧፨᙭᙮᛫᛬᛭។៕៖៚‼‽⁇⁈⁉⸮、。꓾꓿꘍꘎꘏꤯﹐﹑﹒﹔﹕﹖﹗！，．：；？｡､'
# \p{Sterm} = '! .  ?՜՞։؟܀   ܁     ܂߹।॥၊။               ።፧፨  ᙮᜵᜶        ‼‽⁇⁈⁉⸮ 。 ꓿ ꘎꘏꤯﹒     ﹖﹗！．    ？｡'

# \p{SB=AT} = .
# \p{SB=ST} =   ! ?
# \p{Term}  = . ! ? , : ;
# \p{Sterm} = . ! ?

# \u002c - Latin comma
# \u060c - Arabic comma
# \ufe50 - Small comma
# \uff0c - Fullwidth comma

# […\p{Term}--,،﹐，] - ellipsis + Terms - commas

########NEW FILE########
__FILENAME__ = tests
# coding=utf8

import unittest

from slugify import Slugify
from slugify import slugify, slugify_unicode
from slugify import slugify_url, slugify_filename
from slugify import slugify_ru, slugify_de, slugify_el

from slugify import get_slugify


class SlugifyTestCase(unittest.TestCase):

    def test_slugify_english(self):
        self.assertEqual(slugify('This % is a test ---'), 'This-is-a-test')
        self.assertEqual(slugify('_this_is_a__test___'), 'this-is-a-test')
        self.assertEqual(slugify('- - -This -- is a ## test ---'), 'This-is-a-test')

    def test_slugify_umlaut(self):
        self.assertEqual(slugify('kožušček'), 'kozuscek',)
        self.assertEqual(slugify('C\'est déjà l\'été.'), 'Cest-deja-lete')
        self.assertEqual(slugify('jaja---lol-méméméoo--a'), 'jaja-lol-mememeoo-a')
        self.assertEqual(slugify('Nín hǎo. Wǒ shì zhōng guó rén'), 'Nin-hao-Wo-shi-zhong-guo-ren')
        self.assertEqual(slugify('Programmes de publicité - Solutions d\'entreprise'), 'Programmes-de-publicite-Solutions-dentreprise')

    def test_slugify_chinese(self):
        self.assertEqual(slugify('北亰'), 'Bei-Jing')

    def test_slugify_russian(self):
        self.assertEqual(slugify('Компьютер'), 'Kompiuter')
        self.assertEqual(slugify('Транслитерирует и русский'), 'Transliteriruet-i-russkii')
        self.assertEqual(slugify('ёжик из щуки сварил уху'), 'iozhik-iz-shchuki-svaril-ukhu')
        self.assertEqual(slugify('Ах, Юля-Юля'), 'Akh-Iulia-Iulia')

    def test_slugify_ru(self):
        self.assertEqual(slugify_ru('Компьютер'), 'Komputer')
        self.assertEqual(slugify_ru('Транслитерирует и русский'), 'Transliteriryet-i-rysskii')
        self.assertEqual(slugify_ru('ёжик из щуки сварил уху'), 'ezhik-iz-schyki-svaril-yhy')
        self.assertEqual(slugify_ru('Ах, Юля-Юля'), 'Ah-Ulya-Ulya')

    def test_slugify_de(self):
        self.assertEqual(slugify_de('Öl und SÜD'), 'Oel-und-SUED')

    def test_greek(self):
        self.assertEqual(slugify_el('ϒ Ϋ υ ϋ ΰ'), 'Y-Y-y-y-y')

    def test_slugify_unicode(self):
        self.assertEqual(slugify_unicode('-=Слово по-русски=-'), u'Слово-по-русски')
        self.assertEqual(slugify_unicode('слово_по_русски'), u'слово-по-русски')


class PredefinedSlugifyTestCase(unittest.TestCase):

    def test_slugify_url(self):
        self.assertEqual(slugify_url('The Über article'), 'uber-article')

    def test_slugify_filename(self):
        self.assertEqual(slugify_filename(u'Дrаft №2.txt'), u'Draft_2.txt')


class ToLowerTestCase(unittest.TestCase):

    def test_to_lower(self):
        self.assertEqual(slugify('Test TO lower', to_lower=True), 'test-to-lower')

    def test_to_lower_arg(self):
        slugify = Slugify()
        slugify.to_lower = True

        self.assertEqual(slugify('Test TO lower'), 'test-to-lower')
        self.assertEqual(slugify('Test TO lower', to_lower=False), 'Test-TO-lower')

    def test_to_lower_with_capitalize(self):
        self.assertEqual(slugify('Test TO lower', to_lower=True, capitalize=True), 'Test-to-lower')


class UpperTestCase(unittest.TestCase):
    def test_full_upper(self):
        self.assertEqual(slugify_ru('ЯНДЕКС'), 'YANDEKS')

    def test_camel_word(self):
        self.assertEqual(slugify_ru('Яндекс'), 'Yandeks')
        self.assertEqual(slugify_ru('UP Яндекс'), 'UP-Yandeks')
        self.assertEqual(slugify_ru('Яндекс UP'), 'Yandeks-UP')

    def test_part_of_word(self):
        self.assertEqual(slugify_de('ÜBERslugify'), 'UEBERslugify')
        self.assertEqual(slugify_de('ÜBERslugifÜ AUF'), 'UEBERslugifUE-AUF')

    def test_at_start_of_sentence(self):
        self.assertEqual(slugify_ru('Я пошёл'), 'Ya-poshel')
        self.assertEqual(slugify_ru('Я Пошёл'), 'Ya-Poshel')
        self.assertEqual(slugify_ru('Я ПОШёл'), 'YA-POSHel')
        self.assertEqual(slugify_ru('Я ПОШЁЛ. Я Пошел'), 'YA-POSHEL-Ya-Poshel')

    def test_at_end_of_sentence(self):
        self.assertEqual(slugify_ru('пошЁЛ Я'), 'poshEL-YA')
        self.assertEqual(slugify_ru('пошЁЛ Я.'), 'poshEL-YA')
        self.assertEqual(slugify_ru('пошёл Я. ПОШЁЛ'), 'poshel-Ya-POSHEL')

    def test_one_letter_words(self):
        self.assertEqual(slugify_ru('Э Я Г Д Е ?'), 'E-Ya-G-D-E')
        self.assertEqual(slugify_ru('UP Э Я Г Д Е ?'), 'UP-E-YA-G-D-E')

    def test_abbreviation(self):
        self.assertEqual(slugify_ru('UP Я.Б.Ч'), 'UP-Ya-B-Ch')


class PretranslateTestCase(unittest.TestCase):

    def test_pretranslate(self):
        EMOJI_TRANSLATION= {
            u'ʘ‿ʘ': u'smiling',
            u'ಠ_ಠ': u'disapproval',
            u'♥‿♥': u'enamored',
            u'♥': u'love',

            u'(c)': u'copyright',
            u'©': u'copyright',
        }
        slugify_emoji = Slugify(pretranslate=EMOJI_TRANSLATION)
        self.assertEqual(slugify_emoji(u'ʘ‿ʘ'), u'smiling')
        self.assertEqual(slugify_emoji(u'ಠ_ಠ'), u'disapproval')
        self.assertEqual(slugify_emoji(u'(c)'), u'copyright')
        self.assertEqual(slugify_emoji(u'©'), u'copyright')

    def test_pretranslate_lambda(self):
        slugify_reverse = Slugify(pretranslate=lambda value: value[::-1])
        self.assertEqual(slugify_reverse('slug'), 'guls')

    def test_wrong_argument_type(self):
        self.assertRaises(ValueError, lambda: Slugify(pretranslate={1, 2}))


class SanitizeTestCase(unittest.TestCase):
    def test_sanitize(self):
        self.assertEqual(slugify('test_sanitize'), 'test-sanitize')

    def test_safe_chars(self):
        slugify = Slugify()

        slugify.safe_chars = '_'
        self.assertEqual(slugify('test_sanitize'), 'test_sanitize')

        slugify.safe_chars = "'"
        self.assertEqual(slugify('Конь-Огонь'), "Kon'-Ogon'")


class StopWordsTestCase(unittest.TestCase):
    def test_stop_words(self):
        slugify = Slugify(stop_words=['a', 'the'])

        self.assertEqual(slugify('A red apple'), 'red-apple')
        self.assertEqual(slugify('The4 red apple'), 'The4-red-apple')

        self.assertEqual(slugify('_The_red_the-apple'), 'red-apple')
        self.assertEqual(slugify('The__red_apple'), 'red-apple')

        slugify.safe_chars = '*'
        self.assertEqual(slugify('*The*red*apple'), '*-*red*apple')
        self.assertEqual(slugify('The**red*apple'), '**red*apple')

        slugify.stop_words = ['x', 'y']
        self.assertEqual(slugify('x y n'), 'n')

class TruncateTestCase(unittest.TestCase):

    def test_truncate(self):
        self.assertEqual(slugify('one two three four', max_length=7), 'one-two')
        self.assertEqual(slugify('one two three four', max_length=8), 'one-two')
        self.assertEqual(slugify('one two three four', max_length=12), 'one-two-four')
        self.assertEqual(slugify('one two three four', max_length=13), 'one-two-three')
        self.assertEqual(slugify('one two three four', max_length=14), 'one-two-three')

    def test_truncate_on_empty(self):
        self.assertEqual(slugify('', max_length=10), '')

    def test_truncate_short(self):
        self.assertEqual(slugify('dlinnoeslovo', max_length=7), 'dlinnoe')
        self.assertEqual(slugify('dlinnoeslovo и ещё слово', max_length=11), 'dlinnoeslov')

    def test_truncate_long(self):
        self.assertEqual(slugify('шшш щщщ слово', max_length=11), 'shshsh')
        self.assertEqual(slugify('шшш щщщ слово', max_length=12), 'shshsh-slovo')
        self.assertEqual(slugify('шшш щщщ слово', max_length=18), 'shshsh-slovo')
        self.assertEqual(slugify('шшш щщщ слово', max_length=19), 'shshsh-shchshchshch')
        self.assertEqual(slugify('шшш щщщ слово', max_length=24), 'shshsh-shchshchshch')
        self.assertEqual(slugify('шшш щщщ слово', max_length=25), 'shshsh-shchshchshch-slovo')

    def test_truncate_unwanted(self):
        self.assertEqual(slugify('...one...two...three...four...', max_length=12), 'one-two-four')

    def test_truncate_long_separator(self):
        self.assertEqual(slugify('one two three four', max_length=14, separator='...'), 'one...two')


class OtherTestCase(unittest.TestCase):

    def test_prevent_double_pretranslation(self):
        slugify = Slugify(pretranslate={'s': 'ss'})
        self.assertEqual(slugify('BOOST'), 'BOOSST')

    def test_capitalize(self):
        self.assertEqual(slugify('this Is A test', capitalize=True), 'This-Is-A-test')

    def test_capitalize_on_empty(self):
        self.assertEqual(slugify('', capitalize=True), '')


class DeprecationTestCase(unittest.TestCase):

    def test_deprecated_get_slugify(self):
        import warnings

        with warnings.catch_warnings(record=True) as warning:
            warnings.simplefilter('once')

            slugify = get_slugify()
            self.assertEqual(slugify('This % is a test ---'), 'This-is-a-test')
            self.assertIn("'slugify.get_slugify' is deprecated", str(warning[-1].message))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
