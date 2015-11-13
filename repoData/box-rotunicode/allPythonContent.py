__FILENAME__ = rotunicode
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import codecs
import strop


class RotUnicode(codecs.Codec):
    """
    Codec for converting between a string of ASCII and Unicode chars
    maintaining readability.

    >>> codes.register(RotUnicode.search_function)
    >>> 'Hello Frodo!'.encode('rotunicode')
    Ĥȅľľő Ƒŕőďő!
    >>> 'Ĥȅľľő Ƒŕőďő!'.decode('rotunicode')
    Hello Frodo!

    RotUnicode stands for rotate-to-unicode. Or rotten-unicode for those who
    have nightmares about Unicode. It was inspired by Rot13.
    """
    # pylint: disable=no-init
    # The base class does not define it.

    _codec_name = 'rotunicode'

    _ascii_alphabet = strop.lowercase + strop.uppercase + '0123456789'
    _rot_unicode_alphabet = ('ȁƄćďȅƒġĥȉĵƙľḿńőҏqŕŝƭȕѵŵхŷż' +
                             'ȀβĆĎȄƑĜĤȈĴƘĽḾŃŐΡɊŔŜƬȔѴŴΧŶŻ' +
                             'Ꮎ➀➁➂➃➄➅➆➇➈')

    _encoding_table = dict(
        zip(
            (ord(c) for c in _ascii_alphabet),
            _rot_unicode_alphabet,
        ),
    )

    _decoding_table = dict(
        zip(
            (ord(c) for c in _rot_unicode_alphabet),
            (ord(c) for c in _ascii_alphabet),
        ),
    )

    def encode(self, string, errors='strict'):
        """Return the encoded version of a string.

        :param string:
            The input string to encode.
        :type string:
            `basestring`

        :param errors:
            The error handling scheme. Only 'strict' is supported.
        :type errors:
            `basestring`

        :return:
            Tuple of encoded string and number of input bytes consumed.
        :rtype:
            `tuple` (`unicode`, `int`)
        """
        if errors != 'strict':
            raise UnicodeError('Unsupported error handling {}'.format(errors))

        unicode_string = self._ensure_unicode_string(string)
        encoded = unicode_string.translate(self._encoding_table)
        return encoded, len(string)

    def decode(self, string, errors='strict'):
        """Return the decoded version of a string.

        :param string:
            The input string to decode.
        :type string:
            `basestring`

        :param errors:
            The error handling scheme. Only 'strict' is supported.
        :type errors:
            `basestring`

        :return:
            Tuple of decoded string and number of input bytes consumed.
        :rtype:
            `tuple` (`unicode`, `int`)
        """
        if errors != 'strict':
            raise UnicodeError('Unsupported error handling {}'.format(errors))

        unicode_string = self._ensure_unicode_string(string)
        decoded = unicode_string.translate(self._decoding_table)
        return decoded, len(string)

    @classmethod
    def search_function(cls, encoding):
        """Search function to find 'rotunicode' codec."""
        if encoding == cls._codec_name:
            return codecs.CodecInfo(
                name=cls._codec_name,
                encode=RotUnicode().encode,
                decode=RotUnicode().decode,
            )
        return None

    @classmethod
    def _ensure_unicode_string(cls, string):
        """Returns a unicode string for string.

        :param string:
            The input string.
        :type string:
            `basestring`

        :returns:
            A unicode string.
        :rtype:
            `unicode`
        """
        if not isinstance(string, unicode):
            string = string.decode('utf-8')
        return string

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from os.path import splitext


def ruencode(string, extension=False):
    """Encode a string using 'rotunicode' codec.

    :param string:
        The input string to encode.
    :type string:
        `basestring`

    :param extension:
        True if the entire input string should be encoded.
        False to split the input string using :func:`os.path.splitext` and
        encode only the file name portion keeping the extension as is.
    :type extension:
        `bool`

    :return:
        Encoded string.
    :rtype:
        `unicode`
    """
    if extension:
        file_name = string
        file_ext = ''
    else:
        file_name, file_ext = splitext(string)

    return file_name.encode('rotunicode') + file_ext


def rudecode(string):
    """Decode a string using 'rotunicode' codec.

    :param string:
        The input string to decode.
    :type string:
        `basestring`

    :return:
        Decoded string.
    :rtype:
        `unicode`
    """
    return string.decode('rotunicode')

########NEW FILE########
__FILENAME__ = test_rotunicode
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import codecs
from unittest import TestCase

from box.util.rotunicode import RotUnicode


class RotUnicodeTest(TestCase):
    """Tests for :mod:`box.util.rotunicode.rotunicode`."""

    @classmethod
    def setUpClass(cls):
        super(RotUnicodeTest, cls).setUpClass()
        codecs.register(RotUnicode.search_function)

    def test_encoder_is_searchable_by_name(self):
        encoder = codecs.getencoder('rotunicode')
        self.assertIsNotNone(encoder)

    def test_decoder_is_searchable_by_name(self):
        decoder = codecs.getdecoder('rotunicode')
        self.assertIsNotNone(decoder)

    def test_search_function_returns_none_for_non_rotunicode_encoding(self):
        self.assertIsNone(RotUnicode.search_function('random'))

    def test_encoding_using_unsupported_error_types_raise_exception(self):
        with self.assertRaises(UnicodeError):
            'Hello World!'.encode('rotunicode', 'ignore')
        with self.assertRaises(UnicodeError):
            'Hello World!'.encode('rotunicode', 'replace')
        with self.assertRaises(UnicodeError):
            'Hello World!'.encode('rotunicode', 'xmlcharrefreplace')

    def test_decoding_using_unsupported_error_types_raise_exception(self):
        with self.assertRaises(UnicodeError):
            'Hello World!'.decode('rotunicode', 'ignore')
        with self.assertRaises(UnicodeError):
            'Hello World!'.decode('rotunicode', 'replace')
        with self.assertRaises(UnicodeError):
            'Hello World!'.decode('rotunicode', 'xmlcharrefreplace')

    def test_encoding_zero_length_byte_string_returns_zero_length_unicode_string(self):
        self.assertEqual(
            '',
            b''.encode('rotunicode'),
        )

    def test_decoding_zero_length_byte_string_returns_zero_length_unicode_string(self):
        self.assertEqual(
            '',
            b''.decode('rotunicode'),
        )

    def test_encoding_zero_length_unicode_string_returns_zero_length_unicode_string(self):
        self.assertEqual(
            '',
            ''.encode('rotunicode'),
        )

    def test_decoding_zero_length_unicode_string_returns_zero_length_unicode_string(self):
        self.assertEqual(
            '',
            ''.decode('rotunicode'),
        )

    def test_encoding_byte_string_returns_encoded_unicode_string(self):
        self.assertEqual(
            'Ĥȅľľő Ŵőŕľď!',
            b'Hello World!'.encode('rotunicode'),
        )

    def test_decoding_byte_string_returns_decoded_unicode_string(self):
        self.assertEqual(
            'Hello World!',
            b'Ĥȅľľő Ŵőŕľď!'.decode('rotunicode'),
        )

    def test_encoding_unicode_string_returns_encoded_unicode_string(self):
        self.assertEqual(
            'Ĥȅľľő Ŵőŕľď!',
            'Hello World!'.encode('rotunicode'),
        )

    def test_decoding_unicode_string_returns_decoded_unicode_string(self):
        self.assertEqual(
            'Hello World!',
            'Ĥȅľľő Ŵőŕľď!'.decode('rotunicode'),
        )

    def test_encoding_byte_string_with_unsupported_chars_returns_unicode_string_with_unsupported_chars_unchanged(self):
        self.assertEqual(
            'हेलो Ŵőŕľď!',
            b'हेलो World!'.encode('rotunicode'),
        )

    def test_encoding_unicode_string_with_unsupported_chars_returns_unicode_string_with_unsupported_chars_unchanged(self):
        self.assertEqual(
            'हेलो Ŵőŕľď!',
            'हेलो World!'.encode('rotunicode'),
        )

    def test_decoding_byte_string_with_unsupported_chars_returns_unicode_string_with_unsupported_chars_unchanged(self):
        self.assertEqual(
            'हेलो World!',
            b'हेलो Ŵőŕľď!'.decode('rotunicode'),
        )

    def test_decoding_unicode_string_with_unsupported_chars_returns_unicode_string_with_unsupported_chars_unchanged(self):
        self.assertEqual(
            'हेलो World!',
            'हेलो Ŵőŕľď!'.decode('rotunicode'),
        )

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import codecs
from unittest import TestCase

from box.util.rotunicode import RotUnicode, ruencode, rudecode


class RotUnicodeUtilsTest(TestCase):
    """Tests for :mod:`box.util.rotunicode.utils`."""

    @classmethod
    def setUpClass(cls):
        super(RotUnicodeUtilsTest, cls).setUpClass()
        codecs.register(RotUnicode.search_function)

    def test_ruencode_encodes_string_with_no_extension_using_rotunicode(self):
        self.assertEqual(
            'ҏľȁȉń',
            ruencode('plain'),
        )
        self.assertEqual(
            'ҏľȁȉń',
            ruencode('plain', extension=False),
        )
        self.assertEquals(
            '.ȅхƭȅńŝȉőń',
            ruencode('.extension'),
        )
        self.assertEquals(
            '.ȅхƭȅńŝȉőń',
            ruencode('.extension', extension=False),
        )

    def test_ruencode_encodes_string_skipping_extension_using_rotunicode(self):
        self.assertEqual(
            'ҏľȁȉń.txt',
            ruencode('plain.txt'),
        )
        self.assertEqual(
            'ҏľȁȉń.txt',
            ruencode('plain.txt', extension=False),
        )
        self.assertEquals(
            'ƭŵő.ȅхƭ.sions',
            ruencode('two.ext.sions'),
        )
        self.assertEquals(
            'ƭŵő.ȅхƭ.sions',
            ruencode('two.ext.sions', extension=False),
        )

    def test_ruencode_encodes_string_including_extension_using_rotunicode(self):
        self.assertEqual(
            'ҏľȁȉń.ƭхƭ',
            ruencode('plain.txt', extension=True),
        )
        self.assertEquals(
            'ƭŵő.ȅхƭ.ŝȉőńŝ',
            ruencode('two.ext.sions', extension=True),
        )

    def test_rudecode_decodes_string_using_rotunicode(self):
        self.assertEqual(
            'Hello World!',
            rudecode('Ĥȅľľő Ŵőŕľď!'),
        )

########NEW FILE########
